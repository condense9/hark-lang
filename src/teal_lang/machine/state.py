"""Machine state representation"""

from .types import TlType

# TODO convert this class to TealSerialisable, there's duplicated logic. Sorry -
# it came earlier in the design, and is slightly non-trivial to change.


class State:
    """Data local/specific to a particular thread"""

    def __init__(self, data):
        self.ip = 0
        self._ds = list(data)
        self.stopped = False
        self.bindings = {}
        self.error_msg = None
        self.current_arec_ptr = None

    def ds_push(self, val):
        if not isinstance(val, TlType):
            raise TypeError(f"Cannot store {val} ({type(val)})")
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

    def __eq__(self, other):
        return self.serialise() == other.serialise()

    def __str__(self):
        return f"<State {id(self)} ip={self.ip}>"

    def serialise(self):
        return dict(
            ip=self.ip,
            stopped=self.stopped,
            ds=[value.serialise() for value in self._ds],
            bindings={name: value.serialise() for name, value in self.bindings.items()},
            error_msg=self.error_msg,
            current_arec_ptr=self.current_arec_ptr,
        )

    @classmethod
    def deserialise(cls, data: dict):
        s = cls([])
        s.ip = data["ip"]
        s.stopped = data["stopped"]
        s._ds = [TlType.deserialise(obj) for obj in data["ds"]]
        s.bindings = {
            name: TlType.deserialise(val) for name, val in data["bindings"].items()
        }
        s.error_msg = data["error_msg"]
        s.current_arec_ptr = data["current_arec_ptr"]
        return s
