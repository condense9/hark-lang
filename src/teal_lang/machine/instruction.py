"""The Teal Machine Instruction class"""

from .types import TlType
from ..exceptions import UnexpectedError


class BadOperandsLength(UnexpectedError):
    """Wrong number of operands for instruction"""

    def __init__(self, instr_name: str, num_ops: int, expected_num: int):
        msg = (
            f"Wrong number of operands ({num_ops}, expected {expected_num}) "
            f"for {instr_name.upper()}."
        )
        super().__init__(msg)


class BadOperandsType(UnexpectedError):
    """Bad operand type(s) for instruction"""

    def __init__(self, instr_name: str, got, expected, pos: int):
        msg = (
            f"Wrong operand type (got {got}, expected {expected} "
            f"in position {pos}) for {instr_name.upper()}."
        )
        super().__init__(msg)


class Instruction:
    """A Teal Machine bytecode instruction"""

    num_ops = None
    op_types = None
    check_op_types = True

    @classmethod
    def from_node(cls, ast_node, *operands):
        source = [
            str(ast_node.source_filename),  # ensure types are correct
            int(ast_node.source_lineno),
            str(ast_node.source_line),
            int(ast_node.source_column),
        ]
        return cls(*operands, source=source)

    def __init__(self, *operands, source: list = None):
        self.name = type(self).__name__
        self.source = source or [None, None, None, None]

        # All operands *must* be TlType so that the instruction can be
        # serialised
        for idx, o in enumerate(operands):
            if not isinstance(o, TlType):
                raise BadOperandsType(self.name, type(o), TlType, idx)

        if self.num_ops:
            if len(operands) != self.num_ops:
                raise BadOperandsLength(self.name, len(operands), self.num_ops)

        if self.op_types:
            for idx, (a, b) in enumerate(zip(operands, self.op_types)):
                ok = callable(a) if b == callable else isinstance(a, b)
                if not ok:
                    raise BadOperandsType(self.name, type(a), b, idx)

        self.operands = operands

    def serialise(self) -> list:
        """Serialise"""
        operands = [o.serialise() for o in self.operands]
        return [self.name, operands, self.source]

    @classmethod
    def deserialise(cls, obj: list, instruction_set):
        """Deserialise an Instruction

        instruction_set: Module of Instruction types
        """
        name = obj[0]
        operands = [TlType.deserialise(o) for o in obj[1]]
        source = obj[2]
        return getattr(instruction_set, name)(*operands, source=source)

    def __repr__(self):
        ops = ", ".join(map(str, self.operands))
        name = self.name.upper()
        return f"{name:8} {ops}"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )
