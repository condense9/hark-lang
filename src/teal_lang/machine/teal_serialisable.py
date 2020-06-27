"""TealSerialisable class"""
import datetime
from dataclasses import asdict, dataclass


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


def now_str() -> str:
    return datetime.datetime.now().isoformat()
