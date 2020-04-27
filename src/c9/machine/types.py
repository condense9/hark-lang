"""Primitives data types

Requirement: all types must be trivially JSON serialisable.

See https://docs.python.org/3/library/json.html#py-to-json-table
"""

from collections import UserList, UserDict


class C9Type:
    """Base class"""

    def __repr__(self):
        return f"<{type(self).__name__}>"

    def __eq__(self, other):
        return type(self) == type(other)

    def serialise(self) -> list:
        return [type(self).__name__, self.serialise_data()]

    @classmethod
    def deserialise(cls, obj: list):
        name = obj[0]
        new_cls = globals()[name]
        return new_cls.from_data(obj[1])


### Atomics


class C9Atomic(C9Type):
    """Atomic (singleton) types"""

    def serialise_data(self):
        return None

    @classmethod
    def from_data(cls, _):
        return cls()


class C9True(C9Atomic):
    """Represent True"""


class C9False(C9Atomic):
    """Represent False"""


class C9Null(C9Atomic):
    """Represent Null (None)"""


### Literals


class C9Literal(C9Type):
    """A literal data which has an underlying Python type"""

    def __init__(self, value):
        # Restrict to JSON literals (and disallow subclasses of them)
        if type(value) not in (str, float, int):
            raise ValueError(value, type(value))
        self.value = value

    def serialise_data(self):
        return self.value

    @classmethod
    def from_data(cls, value):
        return cls(value)

    def __repr__(self):
        sup = super().__repr__()
        return f"<{sup} {self.value}>"

    def __eq__(self, other):
        return super().__eq__(other) and self.value == other.value


class C9Symbol(str, C9Literal):
    pass


class C9Float(float, C9Literal):
    pass


class C9Int(int, C9Literal):
    pass


class C9String(str, C9Literal):
    pass


class C9Function(str, C9Literal):
    """A function defined in C9"""


class C9Foreign(str, C9Literal):
    """A foreign function"""


class C9Instruction(str, C9Literal):
    """A C9 machine instruction"""


### Complex types


class C9Quote(C9Type):
    """A quoted value"""

    def __init__(self, data):
        self.data = data

    def serialise_data(self):
        # self.data is another C9Type that needs to be serialised
        return self.data.serialise()

    @classmethod
    def from_data(cls, data):
        return cls(C9Type.deserialise(data))


class C9List(UserList, C9Type):
    def serialise_data(self):
        return [a.serialise() for a in self.data]

    @classmethod
    def from_data(cls, data):
        return cls([C9Type.deserialise(a) for a in data])

    def __eq__(self, other):
        return super().__eq__(other) and self.data == other.data


# TODO:
# class C9Dict(UserDict, C9Compound):


# TODO - some kind of "struct" type


class C9FuturePtr(int, C9Literal):
    """Pointer to a C9Future"""


class C9Future(C9Type):
    def __init__(self, ptr, continuations=None, chain=None, resolved=False, value=None):
        self.ptr = ptr
        self.continuations = [] if not continuations else continuations
        self.chain = chain
        self.resolved = resolved
        self.value = value

    def serialise_data(self):
        value = self.value.serialise() if self.value else None
        return [self.ptr, self.continuations, self.chain, self.resolved, value]

    @classmethod
    def from_data(cls, data):
        value = data[-1]
        if data[-1]:
            value = C9Type.deserialise(value)
        return cls(*data[:-1], value)


### Type Mapping

PY_TO_C9 = {
    int: C9Int,
    float: C9Float,
    str: C9String,
    list: C9List,
}


C9_TO_PY = {
    C9Null: lambda _: None,
    C9False: lambda _: False,
    C9True: lambda _: True,
    C9Int: int,
    C9Float: float,
    C9String: str,
    C9List: list,
}


def to_c9_type(py_val):
    if py_val is None:
        return C9Null()
    elif py_val is True:
        return C9True()
    elif py_val is False:
        return C9False()

    try:
        return PY_TO_C9[type(py_val)](py_val)
    except KeyError:
        raise TypeError(type(py_val))


def to_py_type(c9_val):
    try:
        return C9_TO_PY[type(c9_val)](c9_val)
    except KeyError:
        raise TypeError(type(c9_val))
