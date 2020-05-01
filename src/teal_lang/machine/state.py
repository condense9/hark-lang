"""Machine state representation"""

from collections import deque
from .types import TlList, TlType, TlFuturePtr


class State:
    """Entirely represent the state of a machine execution."""

    def __init__(self, *values):
        self._bindings = {}  # ........ local bindings
        self._bs = deque()  # ......... binding stack
        self._ds = deque(values)  # ... data stack
        self._es = deque()  # ......... execution stack
        self.ip = 0  # ................ instruction pointer
        self.stopped = False

    def set_bind(self, ptr, val):
        if not isinstance(val, TlType):
            raise TypeError(val)
        self._bindings[ptr] = val

    def get_bind(self, ptr):
        return self._bindings[ptr]

    @property
    def bound_names(self):
        return list(self._bindings.keys())

    def ds_push(self, val):
        if not isinstance(val, TlType):
            raise TypeError(val)
        self._ds.append(val)

    def ds_pop(self):
        return self._ds.pop()

    def ds_peek(self, offset):
        """Peek at the Nth value from the top of the stack (0-indexed)"""
        return self._ds[-(offset + 1)]

    def ds_set(self, offset, val):
        """Set the value at offset in the stack"""
        if not isinstance(val, TlType):
            raise TypeError(val)
        self._ds[-(offset + 1)] = val

    def es_enter(self, new_ip):
        self._es.append(self.ip)
        self.ip = new_ip
        self._bs.append(self._bindings)
        self._bindings = {}

    def can_return(self):
        return len(self._es) > 0

    def es_return(self):
        self.ip = self._es.pop()
        self._bindings = self._bs.pop()

    def show(self):
        print(self.to_table())

    def to_table(self):
        return (
            "Bind: "
            + ", ".join(f"{k}->{v}" for k, v in self._bindings.items())
            + f"\nData: {self._ds}"
            + f"\nEval: {self._es}"
        )

    def serialise(self):
        all_bindings = list(self._bs) + [self._bindings]
        return dict(
            ip=self.ip,
            stopped=self.stopped,
            es=list(self._es),
            ds=[value.serialise() for value in self._ds],
            all_bindings=[
                {name: value.serialise() for name, value in frame.items()}
                for frame in all_bindings
            ],
        )

    @classmethod
    def deserialise(cls, data: dict):
        bindings = [
            {name: TlType.deserialise(val) for name, val in frame.items()}
            for frame in data["all_bindings"]
        ]
        s = cls()
        s.ip = data["ip"]
        s._stopped = data["stopped"]
        s._es = deque(data["es"])
        s._ds = deque(TlType.deserialise(obj) for obj in data["ds"])
        s._bs = deque(bindings[:-1])
        s._bindings = bindings[-1]
        return s

    def __eq__(self, other):
        return self.serialise() == other.serialise()

    def __repr__(self):
        return f"<State {id(self)} ip={self.ip}>"
