"""The Teal Machine Executable class

Think about this like a Lisp Image - contains all definitions and data required.
You can fire up a machine with one of these, and then evaluate things (run
functions, inspect data, etc).

"""

from dataclasses import dataclass
from typing import Any, Dict

from . import instructionset
from .instruction import Instruction


@dataclass
class Executable:
    bindings: dict
    locations: dict
    code: list
    # data: dict  # TODO

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

    def serialise(self):
        code = [i.serialise() for i in self.code]
        return dict(locations=self.locations, foreign=self.foreign, code=code)

    @classmethod
    def deserialise(cls, obj):
        code = [Instruction.deserialise(i, instructionset) for i in obj["code"]]
        return cls(locations=obj["locations"], foreign=obj["foreign"], code=code)


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
