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
    def __init__(self):
        self.machine_thread = {}
        self.to_join = deque()
        threading.excepthook = self.threading_excepthook
        self.exception = None

    def threading_excepthook(self, args):
        self.exception = args

    def run_machine(self, m):
        thread = threading.Thread(target=m.run)
        self.machine_thread[m] = thread
        thread.start()

    def stop(self, m):
        self.to_join.append(self.machine_thread[m])

    def cleanup(self):
        while self.to_join:
            self.to_join.pop().join()


class LocalRuntime(Runtime):
    """The local runtime is special, as it can manage concurrency locally"""

    def __init__(self, executable, *, probe=DummyProbe):
        C9Machine.count = 0
        self.sleep_interval = 0.01
        self.executable = executable
        self.probe_cls = probe
        self.machine_future = {}
        self.finished = False
        self.result = None
        self.executor = Executor()

    @property
    def machines(self):
        return self.machine_future.keys()

    @property
    def probes(self):
        return [m.probe for m in self.machines]

    def _new_probe(self):
        if self.probe_cls:
            # FIXME probe should handle count
            p = self.probe_cls(name=f"P{len(self.probes)+1}")
            return p
        else:
            return None

    def _new_machine(self, state, future, probe):
        """Start a machine to resolve the given future"""
        m = C9Machine(self.executable, state, self, probe=probe)
        self.machine_future[m] = future
        return m

    def is_future(self, val):
        return isinstance(val, Future)

    def fork(self, from_machine, fn_name, args):
        # Call a function in a new machine, returning a future
        state = LocalState(*args)
        state.ip = self.executable.locations[fn_name]
        future = Future()
        probe = self._new_probe()
        m = self._new_machine(state, future, probe)
        probe.log(f"Fork {from_machine} to {m} => {future}")
        self.executor.run_machine(m)
        return future

    def maybe_wait(self, machine, offset) -> bool:
        future = machine.state.ds_peek(offset)
        assert isinstance(future, Future)
        if future.resolved:
            machine.state.ds_set(offset, future.value)
            return False
        machine.probe.log(f"Waiting on {future}")
        future.add_callback(self._make_continuation(machine, offset))
        return True

    # context: RUNTIME
    def _make_continuation(self, machine, offset):
        """Continue the given machine, updating the value in the stack"""

        def _cont(future, value):
            machine.state.ds_set(offset, value)
            machine.state.stopped = False
            machine.probe.log(f"{future} resolved, continuing {machine}")
            self.executor.run_machine(machine)

        return _cont

    def on_stopped(self, machine):
        self.executor.stop(machine)
        machine.probe.log(f"Stopped {machine}")

    def on_terminated(self, machine):
        # return from top-level
        future = self.machine_future[machine]
        value = machine.state.ds_pop()
        future.resolve(value)
        if future.resolved:
            machine.probe.log(f"Resolved {future}")
        else:
            machine.probe.log(f"Chained {future} to {value}")

    def _finish(self, _, value):
        self.result = value
        self.finished = True

    def run(self, *args):
        initial_state = LocalState(*args)
        top_future = Future()
        top_future.add_callback(self._finish)
        probe = self._new_probe()

        m = self._new_machine(initial_state, top_future, probe)
        probe.log(f"Top Level {m} => {top_future}")
        self.executor.run_machine(m)

        while not self.finished:
            time.sleep(self.sleep_interval)
            self.executor.cleanup()

            for m in self.machines:
                if m.probe.early_stop:
                    raise Exception(f"{m} early stop")

            if self.executor.exception:
                raise Exception("A thread died") from self.executor.exception.exc_value

        if not all(m.stopped for m in self.machines):
            raise Exception("Terminated, but not all machines stopped!")

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
