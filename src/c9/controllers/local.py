"""Local Implementation"""
import importlib
import concurrent.futures
from functools import singledispatchmethod
import logging
import sys
import threading
import time
import traceback
import warnings

from ..machine import C9Machine
from ..machine.controller import Controller as BaseController
from ..machine.future import ChainedFuture
from ..machine.state import State
from ..machine.probe import Probe
from ..machine import c9e
from ..machine.instruction import Instruction
from ..machine import instructionset as mi

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class LocalFuture(ChainedFuture):
    def __init__(self, controller):
        self.lock = threading.Lock()
        self.continuations = []
        self.chain = None
        self.resolved = False
        self.value = None
        self.controller = controller

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
        future = LocalFuture(self)
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

    def finish(self, vmid, result):
        if self.is_top_level(vmid):
            self.result = result
            self.finished = True

    def get_result_future(self, vmid):
        return self._machine_future[vmid]

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def set_future_value(self, vmid, offset, value):
        state = self.get_state(vmid)
        state.ds_set(offset, value)
        state.stopped = False

    def get_or_wait(self, vmid, future, offset):
        # prevent race between resolution and adding the continuation
        with future.lock:
            resolved = future.resolved
            if resolved:
                value = future.value
            else:
                future.continuations.append((vmid, offset))
                value = None
        return resolved, value

    def is_future(self, val):
        return isinstance(val, LocalFuture)

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
        t = time.time()
        line = f"{t:5.5f} | {val}"
        self.data_controller.machine_output[self.vmid].append(line)

    @evali.register
    def _(self, i: mi.Future):
        raise NotImplementedError
