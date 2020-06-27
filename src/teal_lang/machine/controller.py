"""Placeholder for the controller class"""

import logging
from typing import List

from . import types as mt
from .arec import ActivationRecord
from .future import Future
from .probe import Probe
from .state import State
from .thread_failure import StackTraceItem, ThreadFailure

LOG = logging.getLogger(__name__)


class ControllerError(Exception):
    """A general controller error"""


class Controller:
    def __init__(self):
        raise NotImplementedError("Must be subclassed")

    def toplevel_machine(self, fn_ptr: mt.TlFunctionPtr, args):
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
        self.set_entrypoint(fn_ptr.identifier)
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

    def _init_thread(self, vmid, fn_ptr, args, arec):
        state = State(args)
        entrypoint_ip = self.executable.locations[fn_ptr.identifier]
        ptr = self.push_arec(vmid, arec)
        state.current_arec_ptr = ptr
        state.ip = entrypoint_ip
        self.set_state(vmid, state)
        future = Future()
        self.set_future(vmid, future)
        self.set_stopped(vmid, False)
        return vmid

    ##

    def push_arec(self, vmid, rec):
        ptr = self.new_arec()
        self.set_arec(ptr, rec)
        if rec.dynamic_chain is not None:
            self.increment_ref(rec.dynamic_chain)
        return ptr

    def pop_arec(self, ptr):
        # If the given ptr has no more references, remove it from storage.
        # Otherwise, just decrement the references.
        collect_garbage = False
        with self.lock_arec(ptr):
            rec = self.decrement_ref(ptr)
            if rec.ref_count == 0:
                self.delete_arec(ptr)
                collect_garbage = True

        # Pop parent records until one is still being used
        if collect_garbage:
            while rec.dynamic_chain:
                with self.lock_arec(ptr):
                    parent = self.decrement_ref(rec.dynamic_chain)
                    if parent.ref_count > 0:
                        break
                self.delete_arec(rec.dynamic_chain)
                rec = parent

        return rec

    ##

    def resolve_future(self, vmid, value):
        """Resolve a machine future, and any dependent futures"""
        if isinstance(value, mt.TlFuturePtr):
            raise TypeError(value)

        future = self.get_future(vmid)
        future.resolved = True
        future.value = value
        self.set_future(vmid, future)

        if self.is_top_level(vmid):
            self.result = mt.to_py_type(value)

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

        if type(vmid) is not int:
            raise TypeError(vmid)

        # Otherwise, VALUE is another future, and we can only resolve this machine's
        # future if VALUE has also resolved. If VALUE hasn't resolved, we "chain"
        # this machine's future to it.
        with self.lock_future(value.vmid):
            next_future = self.get_future(value.vmid)
            if next_future.resolved:
                return (
                    next_future.value,
                    self._resolve_future(vmid, next_future.value),
                )
            else:
                LOG.info("Chaining %s to %s", vmid, value)
                self.set_future_chain(value.vmid, vmid)
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

        with self.lock_future(future_ptr.vmid):
            future = self.get_future(future_ptr.vmid)
            if future.resolved:
                value = future.value
                LOG.info("%s has resolved: %s", future_ptr, value)
            else:
                value = None
                self.add_continuation(future_ptr.vmid, vmid)
                LOG.info("%d waiting on %s", vmid, future_ptr)
                future = self.get_future(future_ptr.vmid)

        return future.resolved, value

    ##

    def stop(self, vmid, finished_ok):
        """Signal that a machine has stopped running"""
        if not finished_ok:
            self.broken = True
        self.set_stopped(vmid, True)

    ##

    def get_failures(self) -> List[ThreadFailure]:
        """Get information about failed threads"""
        results = []
        for vmid in self.get_thread_ids():
            state = self.get_state(vmid)
            if state.error_msg is not None:
                stacktrace = self.get_stacktrace(vmid)
                results.append(
                    ThreadFailure(
                        # --
                        thread=vmid,
                        error_msg=state.error_msg,
                        stacktrace=stacktrace,
                    )
                )
        return results

    def get_stacktrace(self, vmid) -> List[StackTraceItem]:
        """Get a stack trace for a thread"""
        trace = []
        state = self.get_state(vmid)
        arec_ptr = state.current_arec_ptr
        arec = self.get_arec(arec_ptr)

        # Push the current frame
        trace.append(
            StackTraceItem(
                caller_thread=vmid,
                caller_ip=state.ip - 1,  # minus 1: IP is pre-advanced
                caller_fn=arec.function.identifier,
            )
        )

        # And then all parents
        while True:
            arec = self.get_arec(arec_ptr)
            if arec.dynamic_chain is not None:
                parent = self.get_arec(arec.dynamic_chain)
                trace.append(
                    StackTraceItem(
                        caller_thread=parent.vmid,
                        caller_ip=arec.call_site,
                        caller_fn=parent.function.identifier,
                    )
                )
            else:
                break
            arec_ptr = arec.dynamic_chain

        return list(reversed(trace))
