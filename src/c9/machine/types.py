"""Primitives data types"""


class C9Type:
    """Base class"""

    def serialise(self):
        return "foo"


class C9Atomic(C9Type):
    """Atomic (single-value) types"""


class C9Symbol(C9Type, str):
    pass


class C9Quote(C9Atomic):
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return f"<Quote {self.val}>"


class C9Float(C9Atomic, float):
    pass


class C9Int(C9Atomic, int):
    pass


class C9String(C9Atomic, str):
    pass


class C9Bool(C9Atomic, str):
    pass


class C9Function(C9Atomic, str):
    """A function defined in C9"""


class C9Foreign(C9Atomic, str):
    """A foreign function"""


class C9Instruction(C9Atomic, str):
    """A C9 machine instruction"""


class C9True(C9Bool, str):
    def __repr__(self):
        return "True"


class C9Null(C9Atomic, str):
    """Singleton to represent Null"""

    def __repr__(self):
        return "nil"


class C9Compound(C9Type):
    """Structured types"""


class C9List(C9Compound, list):
    pass


class C9Dict(C9Compound, dict):
    pass
