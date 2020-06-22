"""Placeholder for the controller class"""

from dataclasses import dataclass
import logging
from typing import List, Dict, Tuple
from . import types as mt
from .state import State
from .future import Future
from .probe import Probe

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorInfo:
    traceback: list


class Controller:
    # def __init__(self, session_id)

    def toplevel_machine(self, fn_ptr, args):
        """Create a top-level machine"""
        vmid = self.new_thread()
        arec = ActivationRecord(
            function=fn_ptr,
            dynamic_chain=None,
            vmid=vmid,
            call_site=None,
            bindings={},
            ref_count=1,
        )
        self._init_thread(vmid, fn_ptr, args, arec)
        return vmid

    def thread_machine(self, caller_arec_ptr, caller_ip, fn_ptr, args):
        """Create a new thread machine"""
        vmid = self.new_thread()
        arec = ActivationRecord(
            function=fn_ptr,
            dynamic_chain=caller_arec_ptr,
            vmid=vmid,
            call_site=caller_ip - 1,
            bindings={},
            ref_count=1,
        )
        self._init_thread(vmid, fn_ptr, args, arec)
        return vmid

    def push_arec(self, vmid, rec):
        with self.lock:
            ptr = self.new_arec()
            self.set_arec(ptr, rec)
            if rec.dynamic_chain is not None:
                self.increment_ref(rec.dynamic_chain)
        return ptr

    def pop_arec(self, ptr):
        # If the given ptr has no more references, remove it from storage.
        # Otherwise, just decrement the references.
        collect_garbage = False
        with self.lock:  # ie save
            new_count = self.decrement_ref(ptr)
            rec = self.get_arec(ptr)
            if new_count == 0:
                self.delete_arec(ptr)
                collect_garbage = True

        # Pop parent records until one is still being used
        if collect_garbage:
            while rec.dynamic_chain:
                with self.lock:
                    new_count = self.decrement_ref(rec.dynamic_chain)
                    if new_count > 0:
                        break
                parent = self.get_arec(rec.dynamic_chain)
                self.delete_arec(rec.dynamic_chain)
                rec = parent

        return rec

    def _init_thread(self, vmid, fn_ptr, args, arec):
        state = State(args)
        entrypoint_ip = self.executable.locations[fn_ptr.identifier]
        ptr = self.push_arec(vmid, arec)
        state.current_arec_ptr = ptr
        state.ip = entrypoint_ip
        self.set_state(vmid, state)
        future = Future()
        self.set_future(vmid, future)
        probe = Probe()
        self.set_probe(vmid, probe)
        self.set_stopped(vmid, False)
        return vmid

    def resolve_future(self, vmid, value):
        """Resolve a machine future, and any dependent futures"""
        assert not isinstance(value, mt.TlFuturePtr)
        future = self.get_future(vmid)

        future.resolved = True
        future.value = value
        if self.is_top_level(vmid):
            self.result = mt.to_py_type(value)
            self.finished = True

        continuations = future.continuations
        if future.chain:
            continuations += self.resolve_future(future.chain, value)

        LOG.info("Resolved %d to %s. Continuations: %s", vmid, value, continuations)
        return continuations

    def finish(self, vmid, value) -> list:
        """Finish a machine, resolving its future

        Return waiting machines to invoke, and the value to invoke them with

        """
        if not isinstance(value, mt.TlFuturePtr):
            return value, self.resolve_future(vmid, value)

        # Otherwise, VALUE is another future, and we can only resolve this machine's
        # future if VALUE has also resolved. If VALUE hasn't resolved, we "chain"
        # this machine's future to it.
        with self.lock_future(value):
            next_future = self.get_future(value)
            if next_future.resolved:
                return (
                    next_future.value,
                    self._resolve_future(vmid, next_future.value),
                )
            else:
                LOG.info("Chaining %s to %s", vmid, value)
                next_future.chain = vmid
                return None, []

    def get_or_wait(self, vmid, future_ptr):
        """Get the value of a future in the stack, or add a continuation

        Return tuple:
        - resolved (bool): whether the future has resolved
        - value: The data value, or None if not resolved
        """
        if not isinstance(future_ptr, mt.TlFuturePtr):
            raise TypeError(future_ptr)

        if type(vmid) is not int:
            raise TypeError(vmid)

        future = self.get_future(future_ptr)

        if future.resolved:
            value = future.value
            LOG.info("%s has resolved: %s", future_ptr, value)
        else:
            LOG.info("%d waiting on %s", vmid, future_ptr)
            future.continuations.append(vmid)
            value = None

        return future.resolved, value


@dataclass(frozen=True)
class ARecPtr:
    """Pointer to an activation record"""

    arec_idx: int


@dataclass
class ActivationRecord:
    """Like a stack frame, but more general.

    NOTE static_chain: ARecPtr: Not needed - we don't have nested lexical scopes

    """

    function: mt.TlFunctionPtr  # ....... Owner function
    dynamic_chain: ARecPtr  # ........ Pointer to caller activation record
    vmid: int  # ......................
    call_site: int  # .................
    # parameters: List[mt.TlType]  # ...... Function parameters
    bindings: Dict[str, mt.TlType]  # ... Local bindings
    # result: mt.TlType  # ................ Function return value
    ref_count: int  # ................ Number of places this AR is used
