"""StdoutItem class"""
from dataclasses import asdict, dataclass

from .teal_serialisable import TealSerialisable, now_str


@dataclass
class StdoutItem(TealSerialisable):
    thread: int
    text: str
    time: str = None

    def __post_init__(self):
        if self.time is None:
            self.time = now_str()
