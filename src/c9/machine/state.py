"""Machine state representation"""

from collections import deque


class State:
    """Entirely represent the state of a machine execution."""

    def __init__(self, *values):
        self._bindings = {}  # ........ current bindings
        self._bs = deque()  # ......... binding stack
        self._ds = deque(values)  # ... data stack
        self._es = deque()  # ......... execution stack
        self.ip = 0
        self.stopped = False

    def set_bind(self, ptr, value):
        self._bindings[ptr] = value

    def get_bind(self, ptr):
        return self._bindings[ptr]

    def ds_push(self, val):
        self._ds.append(val)

    def ds_pop(self):
        return self._ds.pop()

    def ds_peek(self, offset):
        """Peek at the Nth value from the top of the stack (0-indexed)"""
        return self._ds[-(offset + 1)]

    def ds_set(self, offset, value):
        """Set the value at offset in the stack"""
        self._ds[-(offset + 1)] = value

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

    def to_dict(self):
        return dict(
            ip=self.ip,
            stopped=self.stopped,
            es=list(self._es),
            ds=list(self._ds),
            bs=list(self._bs),
            bindings=self._bindings,
        )

    @classmethod
    def from_dict(cls, value: dict):
        s = cls()
        s.ip = value["ip"]
        s._stopped = value["stopped"]
        s._es = deque(value["es"])
        s._ds = deque(value["ds"])
        s._bs = deque(value["bs"])
        s._bindings = value["bindings"]
        return s

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    def __repr__(self):
        return f"<State {id(self)} ip={self.ip}>"
