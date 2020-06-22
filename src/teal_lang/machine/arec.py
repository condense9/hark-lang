"""Activation Records"""

from dataclasses import dataclass
from typing import Dict, Union

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
    vmid: int  # ......................
    # parameters: List[mt.TlType]  # ...... Function parameters
    bindings: Dict[str, mt.TlType]  # ... Local bindings
    # result: mt.TlType  # ................ Function return value
    ref_count: int  # ................ Number of places this AR is used
    dynamic_chain: Union[ARecPtr, None] = None  # caller activation record
    call_site: Union[int, None] = None

    def serialise(self):
        d = self.to_dict()
        d["function"] = d["function"].serialise()
        d["bindings"] = {
            name: value.serialise() for name, value in d["bindings"].items()
        }
        return d

    @classmethod
    def deserialise(cls, d):
        rec = cls.from_dict(d)
        rec.function = mt.TlType.deserialise(d["function"])
        rec.bindings = {
            name: mt.TlType.deserialise(value) for name, value in d["bindings"].items()
        }
        return rec

    @classmethod
    def sample(cls):
        return cls(
            function=mt.TlFunctionPtr("foo", None),
            dynamic_chain=ARecPtr(0),
            vmid=0,
            ref_count=0,
            call_site=0,
            bindings={"foo": mt.TlString("hello")},
        )
