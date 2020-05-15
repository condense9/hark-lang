"""The Teal Machine Executable class

Think about this like a Lisp Image - contains all definitions and data required.
You can fire up a machine with one of these, and then evaluate things (run
functions, inspect data, etc).

"""

from dataclasses import dataclass
from typing import Any, Dict

from . import instructionset
from .instruction import Instruction
from .types import TlType


@dataclass
class Executable:
    bindings: dict
    locations: dict
    code: list

    def listing(self):
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
        res = ""
        k = "NAME"
        res += f"{k: <14} VALUE\n"
        for k, v in self.bindings.items():
            res += f"{k:.<14} {v}\n"
        return res

    def serialise(self):
        code = [i.serialise() for i in self.code]
        bindings = {name: val.serialise() for name, val in self.bindings.items()}
        return dict(locations=self.locations, bindings=bindings, code=code)

    @classmethod
    def deserialise(cls, obj):
        code = [Instruction.deserialise(i, instructionset) for i in obj["code"]]
        bindings = {
            name: TlType.deserialise(val) for name, val in obj["bindings"].items()
        }
        return cls(locations=obj["locations"], bindings=bindings, code=code)


def link(bindings: Dict[str, Any], functions: Dict[str, list]) -> Executable:
    """Link bindings and functions into a complete Executable"""
    location = 0
    code = []
    locations = {}
    for fn_name, fn_code in functions.items():
        locations[fn_name] = location
        code += fn_code
        location += len(fn_code)

    return Executable(bindings, locations, code)
