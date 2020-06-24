"""TealSerialisable class"""
from dataclasses import dataclass, asdict


@dataclass
class TealSerialisable:
    """A basic serialisation mixin.

    The inheriting class must be a dataclass.

    """

    def serialise(self):
        """Produce a JSON-serialisable object"""
        return asdict(self)

    @classmethod
    def deserialise(cls, item: dict):
        return cls(**item)
