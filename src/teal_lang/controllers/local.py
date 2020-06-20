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


# TODO store:
# - entrypoint function
# - stopped/finished attributes for Threads
# - stopped/finished attributes for Session (stopped if all threads stopped)
# - activation records
# - trigger mechanism


class DataController(Controller):
    def __init__(self):
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0  # always increasing machine counter
        self._arec_idx = 0  # always increasing arec counter
        self._arecs: Dict[ARecPtr, ActivationRecord] = {}
        self.stdout = []  # shared standard output
        self.executable = None
        self._top_level_vmid = None
        self.result = None
        self.finished = False
        self.lock = threading.RLock()

    def push_arec(self, vmid, arec) -> ARecPtr:
        with self.lock:
            ptr = ARecPtr(vmid, self._arec_idx)
            self._arecs[ptr] = arec
            self._arec_idx += 1
        return ptr

    def pop_arec(self, ptr) -> Tuple[ActivationRecord, ActivationRecord]:
        # If the given ptr has no more references, remove it from storage.
        # Otherwise, just decrement the references.
        with self.lock:
            if self._arecs[ptr].ref_count == 1:
                rec = self._arecs.pop(ptr)
            else:
                rec = self._arecs[ptr]
                rec.ref_count -= 1

            parent = self._arecs[rec.dynamic_chain] if rec.dynamic_chain else None
            return rec, parent

    def increment_arec_ref(self, ptr):
        with self.lock:
            self._arecs[ptr].ref_count += 1

    def set_executable(self, exe):
        self.executable = exe

    def _next_vmid(self):
        vmid = self._machine_idx
        self._machine_idx += 1
        return vmid

    def init_machine(self, vmid, fn_ptr, args, arec):
        state = State(args)
        entrypoint_ip = self.executable.locations[fn_ptr.identifier]
        ptr = self.push_arec(vmid, arec)
        state.current_arec_ptr = ptr
        state.ip = entrypoint_ip
        self._machine_state[vmid] = state
        future = fut.Future()
        self._machine_future[vmid] = future
        probe = Probe()
        self._machine_probe[vmid] = probe
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
        self.increment_arec_ref(caller_arec_ptr)
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

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def error(self, vmid, exc):
        """Handle a machine error"""
        raise NotImplementedError

    def _traceback(self, vmid):
        state = self._machine_state[vmid]
        arec_ptr = state.current_arec_ptr
        arec = self._arecs[arec_ptr]

        # minus 1: IP is pre-advanced
        trace = [[vmid, state.ip - 1, arec.function.identifier]]
        while True:
            arec = self._arecs[arec_ptr]
            if arec.dynamic_chain:
                parent = self._arecs[arec.dynamic_chain]
                trace.append(
                    [arec_ptr.thread, arec.call_site, parent.function.identifier]
                )
            else:
                break
            arec_ptr = arec.dynamic_chain

        print("Teal Traceback (most recent call last):")
        for vmid, ip, fn in reversed(trace):
            print(f"~ ({vmid}) {ip} - {fn}")

    def unexpected_error(self, vmid, exc):
        self._traceback(vmid)
        raise exc

    def teal_error(self, vmid, exc):
        self._traceback(vmid)
        raise exc

    def foreign_error(self, vmid, exc):
        self._traceback(vmid)
        raise exc

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
        if not state.stopped:
            raise Exception("Machine isn't stopped after call to `stop`!")

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
