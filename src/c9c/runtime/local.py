"""Local Implementation"""

import concurrent.futures
import copy
import logging
import sys
import threading
import time
import warnings
from collections import deque

from ..machine import C9Machine, Runtime, State

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOGGER = logging.getLogger()
logging.basicConfig()


class LocalState(State):
    def __init__(self, *values):
        self._bindings = {}  # ........ current bindings
        self._bs = deque()  # ......... binding stack
        self._ds = deque(values)  # ... data stack
        self._es = deque()  # ......... execution stack
        self.ip = 0
        self.stopped = False

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

    def es_return(self):
        self.ip = self._es.pop()
        self._bindings = self._bs.pop()

    def dump(self) -> dict:
        return copy.deepcopy(
            dict(
                bindings=self._bindings,
                bs=self._bs,
                ds=self._ds,
                es=self._es,
                ip=self.ip,
            )
        )

    @classmethod
    def from_dump(cls, dump: dict):
        inst = cls()
        inst._bindings = dump["bindings"]
        inst._bs = dump["bs"]
        inst._ds = dump["ds"]
        inst._es = dump["es"]
        inst.ip = dump["ip"]
        return inst

    def copy(self):
        return LocalState.from_dump(self.dump())

    def show(self):
        print(self.to_table())

    def to_table(self):
        return (
            "Bind: "
            + ", ".join(f"{k}->{v}" for k, v in self._bindings.items())
            + f"\nData: {self._ds}"
            + f"\nEval: {self._es}"
        )


# Ignore builtins for now. Not necessary. MFCall (and maybe Map) is the only one
# that would need to be implementation-defined.
#
# So no custom "microcode" for now. 03/12/20


class LocalCoordinator:
    def __init__(self, state, runtime):
        # machine =
        pass


class Future:
    def __init__(self):
        self.resolved = False
        self.value = None
        self.callbacks = []
        self.chain = None

    def add_callback(self, cb):
        self.callbacks.append(cb)

    def resolve(self, value):
        # value: Either Future or not
        if isinstance(value, Future):
            if value.resolved:
                self._do_resolve(value.value)
            else:
                value.chain = self
        else:
            self._do_resolve(value)

    def _do_resolve(self, value):
        self.resolved = True
        self.value = value
        if self.chain:
            self.chain.resolve(value)
        for c in self.callbacks:
            c(self, value)

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"


# on stopped: future.resolve(value)


class Continuation:
    def __init__(self, state, offset):
        self.state = state.copy()
        self.offset = offset


class DummyProbe:
    def __init__(self, *args, **kwargs):
        pass

    def step_cb(self, *args):
        pass

    def log(self, *args):
        pass


class LocalRuntime(Runtime):
    """The local machine is special, as it can manage concurrency locally

    It has a pool of "other threads" which are running their own little
    machines, and sharing futures.

    The top-level machine will stop when no more threads are executing.

    """

    def __init__(self, executable, *, probe=DummyProbe):
        self.sleep_interval = 0.01
        self.executable = executable
        self.machine_thread = {}
        self.machine_future = {}
        self.probe_cls = probe
        self.machine_probe = {}
        self.finished = False
        # self.lock = threading.Lock()  # FIXME
        self.result = None
        self.exception = None
        self.to_join = deque()
        threading.excepthook = self.threading_excepthook

    def threading_excepthook(self, args):
        self.exception = args

    @property
    def probes(self):
        return self.machine_probe.values()

    def _new_probe(self):
        if self.probe_cls:
            p = self.probe_cls(name=f"P{len(self.probes)+1}")
            return p
        else:
            return None

    def _run_machine(self, m):
        thread = threading.Thread(target=m.run)
        self.machine_thread[m] = thread
        thread.start()

    # context: RUNTIME, THREAD
    def _make_new_machine(self, state, future, probe):
        """Start a machine to resolve the given future"""
        m = C9Machine(self.executable, state, self, probe=probe)
        self.machine_future[m] = future
        self.machine_probe[m] = probe
        return m

    def is_future(self, val):
        return isinstance(val, Future)

    # context: THREAD
    def fork(self, from_machine, fn_name, args):
        # Call a function in a new machine, returning a future
        state = LocalState(*args)
        state.ip = self.executable.locations[fn_name]
        future = Future()
        probe = self._new_probe()
        m = self._make_new_machine(state, future, probe)
        probe.log(f"Fork {from_machine} to {m} => {future}")
        self._run_machine(m)
        return future

    # context: THREAD
    # thread-safe: YES
    def maybe_wait(self, machine, offset) -> bool:
        probe = self.machine_probe[machine]
        future = machine.state.ds_peek(offset)
        assert isinstance(future, Future)
        if future.resolved:
            machine.state.ds_set(offset, future.value)
            return False
        future.add_callback(self._make_continuation(machine, offset))
        probe.log(f"Waiting on {future}")
        return True

    # context: RUNTIME
    def _make_continuation(self, machine, offset):
        """Continue the given machine, updating the value in the stack"""

        def _cont(future, value):
            machine.state.ds_set(offset, value)
            machine.state.stopped = False
            probe = self.machine_probe[machine]
            probe.log(f"{future} resolved, continuing {machine}")
            self._run_machine(machine)

        return _cont

    # context: THREAD
    def on_stopped(self, machine):
        self.to_join.append(self.machine_thread[machine])
        self.machine_probe[machine].log(f"Stopped {machine}")

    # context: THREAD
    def on_terminated(self, machine):
        # return from top-level
        future = self.machine_future[machine]
        value = machine.state.ds_pop()
        future.resolve(value)
        probe = self.machine_probe[machine]
        if future.resolved:
            probe.log(f"Resolved {future}")
        else:
            probe.log(f"Chained {future} to {value}")

    def _finish(self, _, value):
        self.result = value
        self.finished = True

    def run(self, *args):
        initial_state = LocalState(*args)
        top_future = Future()
        top_future.add_callback(self._finish)
        probe = self._new_probe()

        m = self._make_new_machine(initial_state, top_future, probe)
        probe.log(f"Top Level {m} => {top_future}")
        self._run_machine(m)

        while not self.finished:
            time.sleep(self.sleep_interval)
            while self.to_join:
                self.to_join.pop().join()

            for m, t in self.machine_thread.items():
                if self.machine_probe[m].early_stop:
                    raise Exception(f"{m} early stop")

            if self.exception:
                raise Exception("A thread died") from self.exception.exc_value

        # FIXME - this sleep is horrendous hack - synchronise things properly
        time.sleep(0.01)
        if not all(m.stopped for m in self.machine_thread.keys()):
            raise Exception("Terminated, but not all machines stopped")

        return self.result


class DebugProbe:
    """A monitoring probe that stops the VM after a number of steps"""

    def __init__(self, *, name="P", max_steps=300):
        self._max_steps = max_steps
        self._step = 0
        self._name = name
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
