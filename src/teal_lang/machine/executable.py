"""The Teal Machine Executable class"""

from dataclasses import dataclass
from typing import Any, Dict, List

from ..cli import interface as ui
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
        print(" /")
        for i, instr in enumerate(self.code):
            if i in self.locations.values():
                funcname = next(
                    k for k in self.locations.keys() if self.locations[k] == i
                )
                print(" | " + ui.primary(f";; {funcname}:"))
            print(f" | {i:4} | {instr}")
        print(" \\")

    def bindings_table(self):
        """Get a pretty table of bindings"""
        spacing = max(len(x) for x in self.bindings.keys()) + 3
        k = "NAME"
        print(f" {k: <{spacing + 2}}VALUE")
        for k, v in self.bindings.items():
            dots = "." * (spacing - len(k))
            k = ui.primary(k)
            print(f" {k} {dots} {v}")

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
