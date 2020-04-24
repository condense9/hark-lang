"""Primitives data types"""


class C9Type:
    """Base class"""


class C9Atomic(C9Type):
    """Atomic (single-value) types"""


class C9Symbol(C9Type, str):
    def __repr__(self):
        s = super().__repr__()
        return f"<Symbol {s}>"


class C9Number(C9Atomic, float):
    pass


class C9String(C9Atomic, str):
    pass


class C9Bool(C9Atomic):
    pass


class C9True(C9Bool):
    pass


class C9False(C9Bool):
    pass


class C9Null(C9Atomic):
    """Singleton to represent Null"""


class C9Compound(C9Type):
    """Structured types"""


class C9List(C9Compound, list):
    pass


class C9Dict(C9Compound, dict):
    pass
