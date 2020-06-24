"""StdoutItem class"""
import time
from dataclasses import asdict, dataclass

from .teal_serialisable import TealSerialisable


@dataclass
class StdoutItem(TealSerialisable):
    thread: int
    text: str
    time: int = None

    def __post_init__(self):
        if self.time is None:
            self.time = time.time()
