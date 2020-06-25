"""Primitives data types

Requirement: all types must be trivially JSON serialisable.

See https://docs.python.org/3/library/json.html#py-to-json-table
"""

from typing import Optional
from collections import UserList, UserDict

from ..teal_parser.nodes import N_Literal

# TODO Convert these to dataclasses


class TlType:
    """Base class"""

    def __repr__(self):
        return f"<{type(self).__name__}>"

    def serialise(self) -> list:
        return [type(self).__name__, self.serialise_data()]

    def __eq__(self, other):
        return self.serialise() == other.serialise()

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


class TlSymbol(str, TlLiteral):
    pass


class TlFloat(float, TlLiteral):
    pass


class TlInt(int, TlLiteral):
    pass


class TlString(str, TlLiteral):
    pass


class TlInstruction(str, TlLiteral):
    """A Teal machine instruction"""


class TlFuturePtr(TlLiteral):
    """Pointer to a TlFuture"""

    def __init__(self, value):
        if type(value) is not int:
            raise TypeError(value)
        super().__init__(value)
        self.vmid = value


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


class TlHash(UserDict, TlType):
    def serialise_data(self):
        return [[k.serialise(), v.serialise()] for k, v in self.data.items()]

    @classmethod
    def from_data(cls, data):
        return cls({TlType.deserialise(k): TlType.deserialise(v) for k, v in data})


class TlFunctionPtr(TlType):
    """Pointer to a function or closure defined in Tl"""

    def __init__(self, identifier: str, stack_ptr: Optional[int] = None):
        if not isinstance(identifier, str):
            raise ValueError(identifier)
        if stack_ptr and not isinstance(stack_ptr, int):
            raise ValueError(stack_ptr)

        self.identifier = identifier
        self.stack_ptr = stack_ptr

    def serialise_data(self):
        return [self.identifier, self.stack_ptr]

    @classmethod
    def from_data(cls, data):
        return cls(data[0], data[1])

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.identifier}>"


class TlForeignPtr(TlType):
    """Pointer to an imported python function"""

    def __init__(self, identifier: str, module: str):
        if not isinstance(identifier, str):
            raise ValueError(identifier)
        if not isinstance(module, str):
            raise ValueError(module)

        self.identifier = identifier
        self.module = module

    def serialise_data(self):
        return [self.identifier, self.module]

    @classmethod
    def from_data(cls, data):
        return cls(data[0], data[1])

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.module}.{self.identifier}>"


### Type Conversion

# NOTE - no conversion to/from Symbols


def to_teal_type_list(lst: list) -> TlList:
    """Recursively convert list to TlList"""
    if type(lst) != list:
        raise ValueError(lst)
    return TlList([to_teal_type(x) for x in lst])


def to_teal_type_dict(dct: dict) -> TlHash:
    """Recursively convert dict to TlHash"""
    if type(dct) != dict:
        raise ValueError(dct)
    return TlHash({to_teal_type(k): to_teal_type(v) for k, v in dct.items()})


PY_TO_TL = {
    int: TlInt,
    float: TlFloat,
    str: TlString,
    list: to_teal_type_list,
    dict: to_teal_type_dict,
    N_Literal: lambda x: to_teal_type(x.value),  # special case to handle parser
}


Tl_TO_PY = {
    TlNull: lambda _: None,
    TlTrue: lambda _: True,
    TlFalse: lambda _: False,
    TlInt: int,
    TlFloat: float,
    TlString: str,
    TlList: list,
    TlHash: dict,
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
        raise TypeError(f"Can't convert {type(py_val)} to a Teal type")


def to_py_type(teal_val: TlType):
    try:
        return Tl_TO_PY[type(teal_val)](teal_val)
    except KeyError:
        raise TypeError(f"Can't convert {type(teal_val)} to a Python type")
