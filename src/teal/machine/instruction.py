"""The Teal Machine Instruction class"""

from .types import TlType


class BadOperandsLength(Exception):
    """Wrong number of operands for instruction"""


class BadOperandsType(Exception):
    """Bad operand type(s) for instruction"""


class Instruction:
    """A Teal Machine bytecode instruction"""

    num_ops = None
    op_types = None
    check_op_types = True

    def __init__(self, *operands):
        self.name = type(self).__name__

        # All operands *must* be TlType so that the instruction can be
        # serialised
        for o in operands:
            if not isinstance(o, TlType):
                raise BadOperandsType(self.name, o, TlType)

        if self.num_ops:
            if len(operands) != self.num_ops:
                raise BadOperandsLength(self.name, len(operands), self.num_ops)

        if self.op_types:
            for a, b in zip(operands, self.op_types):
                ok = callable(a) if b == callable else isinstance(a, b)
                if not ok:
                    raise BadOperandsType(self.name, a, b)

        self.operands = operands

    def serialise(self):
        """Serialise"""
        operands = [o.serialise() for o in self.operands]
        return [self.name, operands]

    @classmethod
    def deserialise(cls, obj, instruction_set):
        """Deserialise an Instruction

        instruction_set: Module of Instruction types
        """
        name = obj[0]
        operands = [TlType.deserialise(o) for o in obj[1]]
        return getattr(instruction_set, name)(*operands)

    def __repr__(self):
        ops = ", ".join(map(str, self.operands))
        name = self.name.upper()
        return f"{name:8} {ops}"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )
