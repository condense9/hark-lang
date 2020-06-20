"""Placeholder for the controller class"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from .types import TlType, TlFunctionPtr
from .state import State
from .future import Future
from .probe import Probe


@dataclass(frozen=True)
class ErrorInfo:
    traceback: list


# TODO implement interface
class Controller:
    def init_machine(self, vmid, fn_ptr, args, arec):
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


@dataclass(frozen=True)
class ARecPtr:
    """Pointer to an activation record"""

    thread: int
    arec_idx: int


@dataclass
class ActivationRecord:
    """Like a stack frame, but more general.

    NOTE static_chain: ARecPtr: Not needed - we don't have nested lexical scopes

    """

    function: TlFunctionPtr  # ....... Owner function
    dynamic_chain: ARecPtr  # ........ Pointer to caller activation record
    vmid: int  # ......................
    call_site: int  # .................
    # parameters: List[TlType]  # ...... Function parameters
    bindings: Dict[str, TlType]  # ... Local bindings
    # result: TlType  # ................ Function return value
    ref_count: int  # ................ Number of places this AR is used
