"""Machine futures"""

from . import types as mt

# Alias
_SerialisedFuture = dict


class Future:
    """A future - holds results of function calls"""

    def __init__(self, *, continuations=None, chain=None, resolved=False, value=None):
        self.continuations = [] if not continuations else continuations
        self.chain = chain
        self.resolved = resolved
        self.value = value

    def serialise(self) -> _SerialisedFuture:
        value = self.value.serialise() if self.value else None
        return dict(
            continuations=self.continuations,
            chain=self.chain,
            resolved=self.resolved,
            value=value,
        )

    @classmethod
    def deserialise(cls, data: _SerialisedFuture):
        if data.get("value", None):
            data["value"] = mt.TlType.deserialise(data["value"])
        return cls(**data)

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"
