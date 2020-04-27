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

from ..machine import C9Machine, c9e
from ..machine import instructionset as mi
from ..machine import types as mt
from ..machine.controller import Controller as BaseController
from ..machine import future as fut
from ..machine.instruction import Instruction
from ..machine.probe import Probe
from ..machine.state import State

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class LocalFuture(fut.Future):
    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"


class DataController:
    def __init__(self):
        # NOTE - could make probes optional, but why?!
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self.machine_output = {}
        self.executable = None
        self._top_level_vmid = None
        self.result = None
        self.finished = False

    def set_executable(self, exe):
        self.executable = exe

    def new_machine(self, args, fn_name, is_top_level=False):
        if fn_name not in self.executable.locations:
            raise Exception(f"Function `{fn_name}` doesn't exist")
        future = LocalFuture()
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

    def stop(self, vmid, state, probe):
        # N/A locally. In other implementations, could sync state
        pass

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def get_future(self, vmid):
        return self._machine_future[vmid]

    def set_future_value(self, vmid, offset, value):
        """Set the value of a future in the stack"""
        state = self.get_state(vmid)
        state.ds_set(offset, value)
        state.stopped = False

    def finish(self, vmid, value) -> list:
        """Finish a machine, and return continuations (other waiting machines)"""
        return fut.finish(self, vmid, value)

    def get_or_wait(self, vmid, future_ptr, offset):
        """Get the value of a future in the stack, or add a continuation"""
        return fut.get_or_wait(self, vmid, future_ptr, offset)

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
