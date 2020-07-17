"""Primitives data types

Requirement: all types must be trivially JSON serialisable.

See https://docs.python.org/3/library/json.html#py-to-json-table
"""

from typing import Optional
from collections import UserList, UserDict

# TODO Convert these to dataclasses


class TlType:
    """Base class"""

    @property
    def __tlname__(self):
        return type(self).__name__

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


BOOLEANS = (TlTrue, TlFalse)


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

    def __init__(self, future_id):
        if type(future_id) not in (int, str):
            raise TypeError(future_id)
        super().__init__(future_id)
        self.vmid = future_id


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
        return cls(*data)

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.identifier}>"


class TlForeignPtr(TlType):
    """Pointer to an imported python function"""

    def __init__(self, identifier: str, module: str, qualified_name: str):
        if not isinstance(identifier, str):
            raise ValueError(identifier)
        if not isinstance(module, str):
            raise ValueError(module)

        self.identifier = identifier
        self.module = module
        self.qualified_name = qualified_name

    def serialise_data(self):
        return [self.identifier, self.module, self.qualified_name]

    @classmethod
    def from_data(cls, data):
        return cls(*data)

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.module}.{self.identifier}>"


### Type Conversion

# NOTE - no conversion to/from Symbols


def py_list_to_tl(lst: list) -> TlList:
    """Recursively convert list to TlList"""
    return TlList([to_teal_type(x) for x in lst])


def tl_list_to_py(lst: TlList) -> list:
    """Recursively convert TlList to list"""
    return [to_py_type(v) for v in lst]


def py_dict_to_tl(dct: dict) -> TlHash:
    """Recursively convert dict to TlHash"""
    return TlHash({to_teal_type(k): to_teal_type(v) for k, v in dct.items()})


def tl_hash_to_py(hsh: TlHash) -> dict:
    """Recursively convert TlHash to dict"""
    return {to_py_type(k): to_py_type(v) for k, v in hsh.items()}


PY_TO_TL = {
    int: TlInt,
    float: TlFloat,
    str: TlString,
    list: py_list_to_tl,
    dict: py_dict_to_tl,
}


Tl_TO_PY = {
    TlNull: lambda _: None,
    TlTrue: lambda _: True,
    TlFalse: lambda _: False,
    TlInt: int,
    TlFloat: float,
    TlString: str,
    TlList: tl_list_to_py,
    TlHash: tl_hash_to_py,
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
