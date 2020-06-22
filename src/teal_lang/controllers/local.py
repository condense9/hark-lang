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
from ..machine.controller import Controller, ActivationRecord, ARecPtr
from ..machine import future as fut
from ..machine.instruction import Instruction
from ..machine.probe import Probe
from ..machine.state import State
from typing import Tuple

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class DataController(Controller):
    def __init__(self):
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_stopped = {}
        self._machine_idx = 0  # always increasing machine counter
        self._arec_idx = 0  # always increasing arec counter
        self._arecs: Dict[ARecPtr, ActivationRecord] = {}
        self.stdout = []  # shared standard output
        self.executable = None
        self.result = None
        self.broken = False
        self.stopped = False
        self._lock = threading.RLock()

    def new_arec(self):
        ptr = self._arec_idx
        self._arec_idx += 1
        return ptr

    def set_arec(self, ptr, rec):
        self._arecs[ptr] = rec

    def increment_ref(self, ptr):
        self._arecs[ptr].ref_count += 1
        return self._arecs[ptr].ref_count

    def decrement_ref(self, ptr):
        self._arecs[ptr].ref_count -= 1
        return self._arecs[ptr].ref_count

    def delete_arec(self, ptr):
        self._arecs.pop(ptr)

    def get_arec(self, ptr):
        try:
            return self._arecs[ptr]
        except KeyError:
            return None

    def lock_arec(self, _):
        return self._lock

    def set_executable(self, exe):
        self.executable = exe

    def new_thread(self):
        vmid = self._machine_idx
        self._machine_idx += 1
        return vmid

    def is_top_level(self, vmid):
        return vmid == 0

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def set_state(self, vmid, state):
        self._machine_state[vmid] = state

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def set_probe(self, vmid, probe):
        self._machine_probe[vmid] = probe

    def set_stopped(self, vmid, stopped: bool):
        self._machine_stopped[vmid] = stopped

    def all_stopped(self):
        return all(self._machine_stopped.values())

    def get_future(self, val):
        if not isinstance(val, int):
            raise TypeError(val)
        return self._machine_future[val]

    def set_future(self, vmid, future: fut.Future):
        self._machine_future[vmid] = future

    def add_continuation(self, fut_ptr, vmid):
        self.get_future(fut_ptr.vmid).continuations.append(vmid)

    def lock_future(self, _):
        return self._lock

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
        # Print to real stdout at the same time. TODO maybe make this behaviour
        # configurable.
        sys.stdout.write(value)
        self.stdout.append(value)
