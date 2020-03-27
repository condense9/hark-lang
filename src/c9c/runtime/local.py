"""Local Implementation"""

import concurrent.futures
import copy
import logging
import sys
import threading
import time
import traceback
import warnings

from ..machine import C9Machine, Controller, Future, Probe, State
from .runtime_utils import maybe_create

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOGGER = logging.getLogger()
logging.basicConfig()


class LocalProbe(Probe):
    """A monitoring probe that stops the VM after a number of steps"""

    count = 0

    def __init__(self, *, max_steps=300):
        self._max_steps = max_steps
        self._step = 0
        LocalProbe.count += 1
        self._name = f"P{LocalProbe.count}"
        self.logs = []
        self.early_stop = False

    def log(self, text):
        self.logs.append(f"*** <{self._name}> {text}")

    def step_cb(self, m):
        self._step += 1
        self.log(f"[step={self._step}, ip={m.state.ip}] {m.instruction}")
        self.logs.append("Data: " + str(tuple(m.state._ds)))
        if self._step >= self._max_steps:
            self.log(f"MAX STEPS ({self._max_steps}) REACHED!! ***")
            self.early_stop = True
            m._stopped = True

    def on_stopped(self, m):
        kind = "Terminated" if m.terminated else "Stopped"
        self.logs.append(f"*** <{self._name}> {kind} after {self._step} steps. ***")
        self.logs.append(m.state.to_table())

    def print_logs(self):
        print("\n".join(self.logs))


class LocalFuture(Future):
    """A chainable future"""

    def __init__(self, controller):
        super().__init__(controller)
        self.lock = threading.Lock()
        self.continuations = []
        self.chain = None
        self.resolved = False
        self._value = None

    @property
    def value(self):
        return self._value

    def set_value(self, value):
        self.resolved = True
        self._value = value

    def add_continuation(self, machine_reference, offset):
        self.continuations.append((machine_reference, offset))


class MRef(int):
    pass


class LocalController(Controller):
    future_type = LocalFuture

    def __init__(self, executable, do_probe=False):
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self.executable = executable
        self.top_level = None
        self.result = None
        self.finished = False
        self.do_probe = do_probe
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def finish(self, result):
        self.result = result
        self.finished = True

    def stop(self, machine):
        assert isinstance(machine, MRef)
        pass  # Could do something like sync the machine's state

    def is_top_level(self, machine):
        assert isinstance(machine, MRef)
        return machine == self.top_level

    def new_machine(self, args, top_level=False) -> MRef:
        m = MRef(self._machine_idx)
        self._machine_idx += 1
        state = State(*args)
        future = LocalFuture(self)
        probe = maybe_create(LocalProbe, self.do_probe)
        self._machine_future[m] = future
        self._machine_state[m] = state
        self._machine_probe[m] = probe
        if top_level:
            if self.top_level:
                raise Exception("Already got a top level!")
            self.top_level = m
        return m

    def probe_log(self, m, msg):
        assert isinstance(m, MRef)
        if self._machine_probe[m]:
            self._machine_probe[m].log(msg)

    def get_future(self, m):
        assert isinstance(m, MRef)
        return self._machine_future[m]

    def get_state(self, m):
        assert isinstance(m, MRef)
        return self._machine_state[m]

    def get_probe(self, m):
        assert isinstance(m, MRef)
        return self._machine_probe[m]

    def _run_machine(self, m):
        assert isinstance(m, MRef)
        state = self.get_state(m)
        probe = self.get_probe(m)
        machine = C9Machine(m, self)
        thread = threading.Thread(target=machine.run)
        thread.start()

    def run_forked_machine(self, m, new_ip):
        state = self.get_state(m)
        state.ip = new_ip
        self._run_machine(m)

    def run_waiting_machine(self, m, offset, value):
        state = self.get_state(m)
        state.ds_set(offset, value)
        state.stopped = False
        self._run_machine(m)

    def run_top_level(self, args):
        m = self.new_machine(args, top_level=True)
        self.probe_log(m, f"Top Level {m}")
        self._run_machine(m)
        return m

    @property
    def machines(self):
        return [self.top_level] + list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]


class ThreadDied(Exception):
    """A thread died"""


def run(executable, *args, do_probe=True, sleep_interval=0.01):
    LocalProbe.count = 0

    controller = LocalController(executable, do_probe=do_probe)
    controller.run_top_level(args)

    try:
        while not controller.finished:
            time.sleep(sleep_interval)

            for probe in controller.probes:
                if probe.early_stop:
                    raise Exception(f"{m} early stop")

            if controller.exception:
                raise ThreadDied from controller.exception.exc_value

        if not all(controller.get_state(m).stopped for m in controller.machines):
            raise Exception("Terminated, but not all machines stopped!")

    except ThreadDied:
        raise

    except Exception as e:
        warnings.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()

    return controller
