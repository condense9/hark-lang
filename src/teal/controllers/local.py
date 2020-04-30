"""Local Implementation"""
import concurrent.futures
import importlib
import logging
import sys
import threading
import time
import traceback
import warnings
from functools import singledispatchmethod

from ..machine import instructionset as mi
from ..machine import types as mt
from ..machine.controller import Controller as BaseController
from ..machine import future as fut
from ..machine.instruction import Instruction
from ..machine.probe import Probe
from ..machine.state import State

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class DataController:
    def __init__(self):
        # NOTE - could make probes optional, but why?!
        self.evaluator_cls = Evaluator
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self.machine_output = {}
        self.executable = None
        self._top_level_vmid = None
        self.result = None
        self.finished = False
        self.lock = threading.RLock()

    def set_executable(self, exe):
        self.executable = exe

    def new_machine(self, args, fn_name, is_top_level=False):
        if fn_name not in self.executable.locations:
            raise Exception(f"Function `{fn_name}` doesn't exist")
        future = fut.Future()
        probe = Probe()
        state = State(*args)
        state.ip = self.executable.locations[fn_name]
        vmid = self._machine_idx
        self._machine_idx += 1
        self._machine_future[vmid] = future
        self._machine_state[vmid] = state
        self._machine_probe[vmid] = probe
        self.machine_output[vmid] = []
        if is_top_level:
            if self._top_level_vmid:
                raise Exception("Already got a top level!")
            self._top_level_vmid = vmid
        return vmid

    def is_top_level(self, vmid):
        return vmid == self._top_level_vmid

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def get_future(self, val):
        # TODO - clean up. This should only take one type. There's some wrong
        # abstraction somewhere.
        if isinstance(val, mt.TlFuturePtr):
            return self._machine_future[val.value]
        else:
            assert type(val) is int
            return self._machine_future[val]

    def set_future_value(self, vmid, offset, value):
        """Set the value of a future in the stack"""
        state = self.get_state(vmid)
        state.ds_set(offset, value)
        state.stopped = False

    def finish(self, vmid, value) -> list:
        """Finish a machine, and return continuations (other waiting machines)"""
        with self.lock:
            return fut.finish(self, vmid, value)

    def get_or_wait(self, vmid, future_ptr, state, probe):
        """Get the value of a future in the stack, or add a continuation"""
        with self.lock:
            # TODO fix race condition? Relevant for local?
            resolved, value = fut.get_or_wait(self, vmid, future_ptr)
            if not resolved:
                state.stopped = True
            return resolved, value

    @property
    def machines(self):
        return list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]

    @property
    def stdout(self):
        return list(self.machine_output.values())


# This is probably unnecessary, and could be part of the data controller, but
# kept separate for now...
class Evaluator:
    """Local implementation of machine instructions"""

    def __init__(self, parent):
        self.vmid = parent.vmid
        self.state = parent.state
        self.data_controller = parent.data_controller

    @singledispatchmethod
    def evali(self, i: Instruction):
        """Evaluate instruction"""
        assert isinstance(i, Instruction)
        raise NotImplementedError(i)

    @evali.register
    def _(self, i: mi.Print):
        # Leave the value in the stack - print returns itself
        val = self.state.ds_peek(0)
        t = time.time() % 1000.0
        line = f"{t:.2f} | {val}"
        self.data_controller.machine_output[self.vmid].append(line)

    @evali.register
    def _(self, i: mi.Future):
        raise NotImplementedError
