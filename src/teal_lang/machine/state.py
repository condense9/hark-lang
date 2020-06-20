"""Machine state representation"""

from typing import Dict, List

from .types import TlFuturePtr, TlList, TlType


class State:
    """Data local/specific to a particular thread"""

    def __init__(self, data):
        self.ip = 0
        self._ds = list(data)
        self.stopped = False
        self.bindings = {}
        self.error = None
        self.traceback = None
        self.current_arec_ptr = None

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

    def show(self):
        print(self.to_table())

    def to_table(self):
        return (
            "Bind: "
            + ", ".join(f"{k}->{v}" for k, v in self.bindings.items())
            + f"\nData: {self._ds}"
        )

    def serialise(self):
        all_bindings = list(self._bs) + [self.bindings]
        return dict(
            ip=self.ip,
            stopped=self.stopped,
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
        s._ds = deque(TlType.deserialise(obj) for obj in data["ds"])
        s._bs = deque(bindings[:-1])
        s.bindings = bindings[-1]
        return s

    def __eq__(self, other):
        return self.serialise() == other.serialise()

    def __repr__(self):
        return f"<State {id(self)} ip={self.ip}>"
