"""Primitives data types"""

from collections import UserList


class C9Type:
    """Base class"""

    def serialise(self) -> list:
        return [type(self).__name__]

    @classmethod
    def deserialise(cls, obj: list):
        name = obj[0]
        new_cls = globals()[name]

        if len(obj) == 1:
            return new_cls()
        elif len(obj) == 2:
            data = obj[1]

            if issubclass(new_cls, C9Compound):
                data = [cls.deserialise(a) for a in data]

            return new_cls(data)
        else:
            raise ValueError(obj)

    def __repr__(self):
        return f"<{type(self).__name__}>"

    def __eq__(self, other):
        return type(self) == type(other)


### Atomics


class C9Atomic(C9Type):
    """Atomic (singleton) types"""


class C9True(C9Atomic):
    """Represent True"""


class C9Null(C9Atomic):
    """Represent Null (False)"""


### Literals


class C9Literal(C9Type):
    """A literal value which has an underlying Python type"""

    def __init__(self, data):
        self.data = data

    def serialise(self) -> list:
        return super().serialise() + [self.data]

    def __repr__(self):
        sup = super().__repr__()
        return f"<{sup} {self.data}>"

    def __eq__(self, other):
        return super().__eq__(other) and self.data == other.data


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


### Compound types


class C9Compound(C9Type):
    def __init__(self, data):
        self.data = data

    def serialise(self) -> list:
        data = [a.serialise() for a in self.data]
        return super().serialise() + [data]

    def __repr__(self):
        sup = super().__repr__()
        return f"<{sup} {self.data}>"

    def __eq__(self, other):
        return super().__eq__(other) and self.data == other.data


class C9Quote(C9Compound):
    """A quoted value"""


class C9List(UserList, C9Compound):
    def __init__(self, data):
        super(C9List, self).__init__(data)


# TODO:
# class C9Dict(C9Compound, dict):
#     pass
