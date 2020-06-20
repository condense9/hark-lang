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
        self._top_level_vmid = None
        self.result = None
        self.broken = False
        self.stopped = False
        self.lock = threading.RLock()

    def push_arec(self, vmid, rec) -> ARecPtr:
        with self.lock:
            ptr = ARecPtr(vmid, self._arec_idx)
            self._arecs[ptr] = rec
            self._arec_idx += 1
            if rec.dynamic_chain:
                self._arecs[rec.dynamic_chain].ref_count += 1
        return ptr

    def pop_arec(self, ptr) -> Tuple[ActivationRecord, ActivationRecord]:
        # If the given ptr has no more references, remove it from storage.
        # Otherwise, just decrement the references.
        with self.lock:
            rec = self._arecs[ptr]
            rec.ref_count -= 1
            if rec.ref_count == 0:
                self._arecs.pop(ptr)

                # Pop parent records until one is still being used
                while rec.dynamic_chain:
                    parent = self._arecs[rec.dynamic_chain]
                    parent.ref_count -= 1
                    if parent.ref_count > 0:
                        break
                    rec = self._arecs.pop(rec.dynamic_chain)

        return rec

    def get_arec(self, ptr: ARecPtr):
        if ptr:
            return self._arecs[ptr]
        else:
            return None

    def set_executable(self, exe):
        self.executable = exe

    def _next_vmid(self):
        vmid = self._machine_idx
        self._machine_idx += 1
        return vmid

    def toplevel_machine(self, fn_ptr, args):
        vmid = self._next_vmid()
        if self._top_level_vmid:
            raise ValueError("Already got a top level!")

        arec = ActivationRecord(
            function=fn_ptr,
            dynamic_chain=None,
            vmid=vmid,
            call_site=None,
            bindings={},
            ref_count=1,
        )
        self.init_machine(vmid, fn_ptr, args, arec)
        self._top_level_vmid = vmid
        return vmid

    def thread_machine(self, caller_arec_ptr, caller_ip, fn_ptr, args):
        vmid = self._next_vmid()
        arec = ActivationRecord(
            function=fn_ptr,
            dynamic_chain=caller_arec_ptr,
            vmid=vmid,
            call_site=caller_ip - 1,
            bindings={},
            ref_count=1,
        )
        self.init_machine(vmid, fn_ptr, args, arec)
        return vmid

    def is_top_level(self, vmid):
        return vmid == self._top_level_vmid

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

    def error(self, vmid, exc):
        """Handle a machine error"""
        raise NotImplementedError

    def get_future(self, val):
        # TODO - clean up. This should only take one type. There's some wrong
        # abstraction somewhere.
        if isinstance(val, mt.TlFuturePtr):
            return self._machine_future[val.value]
        else:
            assert type(val) is int
            return self._machine_future[val]

    def set_future(self, vmid, future: fut.Future):
        self._machine_future[vmid] = future

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
        if not state.stopped:
            raise Exception("Machine isn't stopped after call to `stop`!")
        if state.error:
            self.broken = True
        self.set_stopped(vmid, True)
        if all(self._machine_stopped.values()):
            self.stopped = True

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
