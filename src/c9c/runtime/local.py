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


class Future:
    def __init__(self):
        self.resolved = False
        self.value = None
        self.chain = None
        self.lock = threading.Lock()
        self.continuations = []

    def add_callback(self, cb):
        self.callbacks.append(cb)

    def add_continuation(self, machine, offset):
        self.continuations.append((machine, offset))

    def resolve(self, value):
        # value: Either Future or not
        if isinstance(value, Future):
            if value.resolved:
                self._do_resolve(value.value)
            else:
                value.chain = self
        else:
            self._do_resolve(value)
        return self.resolved

    def _do_resolve(self, value):
        self.resolved = True
        self.value = value
        if self.chain:
            self.chain.resolve(value)
        for machine, offset in self.continuations:
            machine.probe.log(f"{self} resolved, continuing {machine}")
            machine.state.ds_set(offset, value)
            machine.state.stopped = False
            machine.runtime.executor.run_machine(machine)

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"


class Continuation:
    def __init__(self, state, offset):
        self.state = state.copy()
        self.offset = offset


class DummyProbe:
    def __init__(self, *args, **kwargs):
        self.early_stop = False

    def step_cb(self, *args):
        pass

    def log(self, *args):
        pass


class Executor:
    """Execute and manage machines running locally using the threading module"""

    def __init__(self, executable):
        self.executable = executable
        self.machine_thread = {}
        self.machine_future = {}
        self.to_join = deque()
        self.future_type = Future
        threading.excepthook = self.threading_excepthook
        self.exception = None

    @property
    def machines(self):
        return self.machine_future.keys()

    def threading_excepthook(self, args):
        self.exception = args

    def run_machine(self, m):
        assert m in self.machine_future
        thread = threading.Thread(target=m.run)
        self.machine_thread[m] = thread
        thread.start()

    def new_machine(self, runtime, args, *, probe=None, entrypoint_fn=None):
        future = Future()
        state = LocalState(*args)
        if entrypoint_fn:
            state.ip = self.executable.locations[entrypoint_fn]
        machine = C9Machine(self.executable, state, runtime, probe=probe)
        self.machine_future[machine] = future
        return machine, future

    def stop(self, m):
        self.to_join.append(self.machine_thread[m])

    def cleanup(self):
        while self.to_join:
            self.to_join.pop().join()

    def get_future(self, m):
        return self.machine_future[m]


class LocalRuntime(Runtime):
    def __init__(self, executor, *, probe_cls=DummyProbe):
        C9Machine.count = 0
        self.probe_cls = probe_cls
        self.finished = False
        self.result = None
        self.executor = executor
        self.top_level = None

    @property
    def future_type(self):
        return self.executor.future_type

    @property
    def probes(self):
        return [m.probe for m in self.executor.machines]

    def _new_probe(self):
        if self.probe_cls:
            # FIXME probe_cls should handle count
            p = self.probe_cls(name=f"P{len(self.probes)+1}")
            return p
        else:
            return None

    def start_first_machine(self, args):
        probe = self._new_probe()
        m, f = self.executor.new_machine(self, args, probe=probe)
        m.probe.log(f"Top Level {m} => {f}")
        self.top_level = m
        self.executor.run_machine(m)

    def fork(self, from_machine, fn_name, args):
        # Call a function in a new machine, returning a future
        probe = self._new_probe()
        m, f = self.executor.new_machine(self, args, entrypoint_fn=fn_name, probe=probe)
        m.probe.log(f"Fork {from_machine} to {m} => {f}")
        self.executor.run_machine(m)
        return f

    def on_stopped(self, machine):
        self.executor.stop(machine)

    def on_return(self, machine, result):
        # machine returned from top-level (i.e. not a Wait)
        future = self.executor.get_future(machine)
        with future.lock:
            resolved = future.resolve(result)
        if resolved:
            machine.probe.log(f"Resolved {future}")
        else:
            assert machine != self.top_level
            machine.probe.log(f"Chained {future} to {result}")
        if machine == self.top_level and machine.terminated:
            self.result = result
            self.finished = True


def run(executable, *args, probe_cls=None, sleep_interval=0.01):
    executor = Executor(executable)
    runtime = LocalRuntime(executor, probe_cls=probe_cls)

    runtime.start_first_machine(args)

    while not runtime.finished:
        time.sleep(sleep_interval)
        runtime.executor.cleanup()

        for m in runtime.executor.machines:
            if m.probe.early_stop:
                raise Exception(f"{m} early stop")

        if runtime.executor.exception:
            raise Exception("A thread died") from runtime.executor.exception.exc_value

    if not all(m.stopped for m in runtime.executor.machines):
        raise Exception("Terminated, but not all machines stopped!")

    return runtime


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
