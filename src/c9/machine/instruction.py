"""The C9 Machine Instruction class"""


class BadOperandsLength(Exception):
    """Wrong number of operands for instruction"""


class BadOperandsType(Exception):
    """Bad operand type(s) for instruction"""


class Instruction:
    """A C9 Machine bytecode instruction"""

    op_types = []
    check_op_types = True

    def __init__(self, *operands):
        self.name = type(self).__name__

        if len(operands) != len(self.op_types):
            raise BadOperandsLength(self.name, len(operands), len(self.op_types))

        for a, b in zip(operands, self.op_types):
            ok = callable(a) if b == callable else isinstance(a, b)
            if not ok:
                raise BadOperandsType(self.name, a, b)

        self.operands = operands

    def __repr__(self):
        ops = ", ".join(map(str, self.operands))
        name = self.name.upper()
        return f"{name:8} {ops}"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )

    @classmethod
    def from_name(cls, name, *ops):
        """Instantiate a machine instruction with name and operands"""
        # contract: self.name can be looked up here.
        return globals()[name](*ops)
