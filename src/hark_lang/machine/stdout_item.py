"""StdoutItem class"""
from dataclasses import asdict, dataclass

from .hark_serialisable import HarkSerialisable, now_str


@dataclass
class StdoutItem(HarkSerialisable):
    thread: int
    text: str
    time: str = None

    def __post_init__(self):
        if self.time is None:
            self.time = now_str()
