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
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self.stdout = []
        self.executable = None
        self._top_level_vmid = None
        self.result = None
        self.finished = False
        self.lock = threading.RLock()

    def set_executable(self, exe):
        self.executable = exe

    def new_machine(self, args, fn_ptr, is_top_level=False):
        entrypoint_ptr = self.executable.locations[fn_ptr.identifier]
        # TODO retrive a closure's stack frame
        state = State(*args)
        state.ip = entrypoint_ptr
        vmid = self._machine_idx
        future = fut.Future()
        probe = Probe()
        self._machine_idx += 1
        self._machine_future[vmid] = future
        self._machine_state[vmid] = state
        self._machine_probe[vmid] = probe
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

    def get_or_wait(self, vmid, future_ptr, state):
        """Get the value of a future in the stack, or add a continuation"""
        with self.lock:
            # TODO fix race condition? Relevant for local?
            resolved, value = fut.get_or_wait(self, vmid, future_ptr)
            if not resolved:
                state.stopped = True
            return resolved, value

    def stop(self, vmid, state, probe):
        assert state.stopped

    @property
    def machines(self):
        return list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]

    def write_stdout(self, value: str):
        # don't use isinstance - it must be an actual str
        if type(value) != str:
            raise ValueError(f"{value} ({type(value)}) is not str")
        self.stdout.append(value)
