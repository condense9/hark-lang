"""Activation Records"""

from dataclasses import dataclass
from typing import Dict, Union

from ..machine import types as mt
from .teal_serialisable import TealSerialisable

ARecPtr = int


@dataclass
class ActivationRecord(TealSerialisable):
    """Like a stack frame, but more general.

    NOTE static_chain: ARecPtr: Not needed - we don't have nested lexical scopes

    """

    function: mt.TlFunctionPtr  # ....... Owner function
    vmid: int  # ......................
    # parameters: List[mt.TlType]  # ...... Function parameters
    bindings: Dict[str, mt.TlType]  # ... Local bindings
    # result: mt.TlType  # ................ Function return value
    ref_count: int  # ................ Number of places this AR is used
    dynamic_chain: Union[ARecPtr, None] = None  # caller activation record
    call_site: Union[int, None] = None
    deleted: bool = False

    def serialise(self):
        d = super().serialise()
        d["function"] = d["function"].serialise()
        d["bindings"] = {
            name: value.serialise() for name, value in d["bindings"].items()
        }
        return d

    @classmethod
    def deserialise(cls, d):
        d["function"] = mt.TlType.deserialise(d["function"])
        d["bindings"] = {
            name: mt.TlType.deserialise(value) for name, value in d["bindings"].items()
        }
        return super().deserialise(d)
