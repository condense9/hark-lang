"""Activation Records"""

from dataclasses import dataclass
from typing import Dict

from dataclasses_json import dataclass_json

from ..machine import types as mt

ARecPtr = int


@dataclass_json
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

    def serialise(self):
        d = self.to_dict()
        d["function"] = d["function"].serialise()
        return d

    def deserialise(self, a):
        a = self.from_dict(a)
        a.function = mt.TlType.deserialise(a["function"])
        print("HII", type(a))
        return a

    @classmethod
    def sample(cls):
        return cls(
            mt.TlFunctionPtr("foo", None),
            ARecPtr(0),
            0,
            0,
            {"foo", mt.TlString("hello")},
            0,
        )
