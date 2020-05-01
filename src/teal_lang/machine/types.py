"""Primitives data types

Requirement: all types must be trivially JSON serialisable.

See https://docs.python.org/3/library/json.html#py-to-json-table
"""

from collections import UserList, UserDict


class TlType:
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


class TlAtomic(TlType):
    """Atomic (singleton) types"""

    def serialise_data(self):
        return None

    @classmethod
    def from_data(cls, _):
        return cls()


class TlTrue(TlAtomic):
    """Represent True"""


class TlFalse(TlAtomic):
    """Represent False"""


class TlNull(TlAtomic):
    """Represent Null (None)"""


### Literals


class TlLiteral(TlType):
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
        kind = type(self).__name__
        return f"<{kind} {self.value}>"

    def __eq__(self, other):
        return super().__eq__(other) and self.value == other.value


class TlSymbol(str, TlLiteral):
    pass


class TlFloat(float, TlLiteral):
    pass


class TlInt(int, TlLiteral):
    pass


class TlString(str, TlLiteral):
    pass


class TlFunction(str, TlLiteral):
    """A function defined in Tl"""


class TlForeign(str, TlLiteral):
    """A foreign function"""


class TlInstruction(str, TlLiteral):
    """A Teal machine instruction"""


### Complex types


class TlQuote(TlType):
    """A quoted value"""

    def __init__(self, data):
        self.data = data

    def serialise_data(self):
        # self.data is another TlType that needs to be serialised
        return self.data.serialise()

    @classmethod
    def from_data(cls, data):
        return cls(TlType.deserialise(data))


class TlList(UserList, TlType):
    def serialise_data(self):
        return [a.serialise() for a in self.data]

    @classmethod
    def from_data(cls, data):
        return cls([TlType.deserialise(a) for a in data])

    def __eq__(self, other):
        return super().__eq__(other) and self.data == other.data


# TODO:
# class TlDict(UserDict, TlCompound):


# TODO - some kind of "struct" type


class TlFuturePtr(TlLiteral):
    """Pointer to a TlFuture"""

    def __init__(self, value):
        if type(value) is not int:
            raise TypeError(value)
        super().__init__(value)


### Type Conversion

# NOTE - no conversion to/from Symbols

PY_TO_TL = {
    int: TlInt,
    float: TlFloat,
    str: TlString,
    list: TlList,
}


Tl_TO_PY = {
    TlNull: lambda _: None,
    TlTrue: lambda _: True,
    TlFalse: lambda _: False,
    TlInt: int,
    TlFloat: float,
    TlString: str,
    TlList: list,
}


def to_teal_type(py_val):
    if py_val is None:
        return TlNull()
    elif py_val is True:
        return TlTrue()
    elif py_val is False:
        return TlFalse()

    try:
        return PY_TO_TL[type(py_val)](py_val)
    except KeyError:
        raise TypeError(type(py_val))


def to_py_type(teal_val: TlType):
    try:
        return Tl_TO_PY[type(teal_val)](teal_val)
    except KeyError:
        raise TypeError(type(teal_val))
