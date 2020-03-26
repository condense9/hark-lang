"""Local Implementation"""

import concurrent.futures
import copy
import logging
import sys
import threading
import time
import warnings
from collections import deque

from ..machine import C9Machine, State, Future, Probe, Storage, Executor
from .runtime_utils import maybe_create

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOGGER = logging.getLogger()
logging.basicConfig()


class LocalState(State):
    def __init__(self, *values):
        self._bindings = {}  # ........ current bindings
        self._bs = deque()  # ......... binding stack
        self._ds = deque(values)  # ... data stack
        self._es = deque()  # ......... execution stack
        self._ip = 0
        self.stopped = False

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, new_ip):
        self._ip = new_ip

    def set_bind(self, ptr, value):
        self._bindings[ptr] = value

    def get_bind(self, ptr):
        return self._bindings[ptr]

    def ds_push(self, val):
        self._ds.append(val)

    def ds_pop(self):
        return self._ds.pop()

    def ds_peek(self, offset):
        """Peek at the Nth value from the top of the stack (0-indexed)"""
        return self._ds[-(offset + 1)]

    def ds_set(self, offset, value):
        """Set the value at offset in the stack"""
        self._ds[-(offset + 1)] = value

    def es_enter(self, new_ip):
        self._es.append(self.ip)
        self.ip = new_ip
        self._bs.append(self._bindings)
        self._bindings = {}

    def can_return(self):
        return len(self._es) > 0

    def es_return(self):
        self.ip = self._es.pop()
        self._bindings = self._bs.pop()

    def show(self):
        print(self.to_table())

    def to_table(self):
        return (
            "Bind: "
            + ", ".join(f"{k}->{v}" for k, v in self._bindings.items())
            + f"\nData: {self._ds}"
            + f"\nEval: {self._es}"
        )


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

    def __init__(self, storage):
        self.storage = storage
        self.resolved = False
        self.value = None
        self.chain = None
        self.lock = threading.Lock()
        self.continuations = []

    def add_continuation(self, machine, offset):
        self.continuations.append((machine.m_id, offset))

    def __repr__(self):
        return f"<LocalFuture {id(self)} {self.resolved} ({self.value})>"


class MRef(int):
    pass


class LocalStorage(Storage):
    future_type = LocalFuture

    def __init__(self, executable, executor, do_probe=False):
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self._executor = executor
        self.executable = executable
        self.top_level = None
        self.result = None
        self.finished = False
        self.do_probe = do_probe

    def finish(self, result):
        self.result = result
        self.finished = True

    def is_top_level(self, machine):
        assert isinstance(machine, MRef)
        return machine == self.top_level

    def new_machine(self, args, top_level=False) -> MRef:
        m = MRef(self._machine_idx)
        self._machine_idx += 1
        state = LocalState(*args)
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

    def push_machine_to_run(self, m):
        assert isinstance(m, MRef)
        self._executor.run(self, m)

    def pop_machine_to_run(self):
        return None

    @property
    def machines(self):
        return [self.top_level] + list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]


class LocalExecutor(Executor):
    """Execute and manage machines running locally using the threading module"""

    future_type = LocalFuture

    def __init__(self):
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def run(self, storage, machine):
        state = storage.get_state(machine)
        probe = storage.get_probe(machine)
        m = C9Machine(machine, storage)
        thread = threading.Thread(target=m.run)
        thread.start()


def run(executable, *args, do_probe=True, sleep_interval=0.01):
    # C9Machine.count = 0
    LocalProbe.count = 0

    executor = LocalExecutor()
    storage = LocalStorage(executable, executor, do_probe=do_probe)
    machine = storage.new_machine(args, top_level=True)

    storage.probe_log(machine, f"Top Level {machine}")
    executor.run(storage, machine)

    try:
        while not storage.finished:
            time.sleep(sleep_interval)

            for probe in storage.probes:
                if probe.early_stop:
                    raise Exception(f"{m} early stop")

            if executor.exception:
                raise Exception("A thread died") from executor.exception.exc_value

        if not all(storage.get_state(m).stopped for m in storage.machines):
            raise Exception("Terminated, but not all machines stopped!")
    finally:
        return storage
