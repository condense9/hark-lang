"""The Teal Machine Executable class"""

from dataclasses import dataclass
from typing import Any, Dict, List

from . import instructionset
from .instruction import Instruction
from .types import TlType


@dataclass
class Executable:
    """Teal executable"""

    bindings: Dict[str, TlType]
    locations: Dict[str, int]
    code: List[Instruction]
    attributes: dict

    def listing(self) -> str:
        """Get a pretty assembly listing string"""
        res = " /\n"
        for i, instr in enumerate(self.code):
            if i in self.locations.values():
                funcname = next(
                    k for k in self.locations.keys() if self.locations[k] == i
                )
                res += f" | ;; {funcname}:\n"
            res += f" | {i:4} | {instr}\n"
        res += " \\\n"
        return res

    def bindings_table(self):
        """Get a pretty table of bindings"""
        spacing = max(len(x) for x in self.bindings.keys()) + 5
        res = ""
        k = "NAME"
        res += f" {k: <{spacing}}VALUE\n"
        for k, v in self.bindings.items():
            res += f" {k:.<{spacing}}{v}\n"
        return res

    def serialise(self) -> dict:
        """Serialise the executable into a JSON-able dict"""
        code = [i.serialise() for i in self.code]
        bindings = {name: val.serialise() for name, val in self.bindings.items()}
        return dict(locations=self.locations, bindings=bindings, code=code)

    @classmethod
    def deserialise(cls, obj: dict):
        """Deserialise the dict created by serialise"""
        code = [Instruction.deserialise(i, instructionset) for i in obj["code"]]
        bindings = {
            name: TlType.deserialise(val) for name, val in obj["bindings"].items()
        }
        # FIXME attributes
        return cls(
            locations=obj["locations"], bindings=bindings, code=code, attributes=None
        )
