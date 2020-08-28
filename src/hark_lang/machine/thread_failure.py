"""ThreadFailure class"""
import time
from dataclasses import asdict, dataclass
from typing import List

from .hark_serialisable import HarkSerialisable


@dataclass
class StackTraceItem(HarkSerialisable):
    caller_thread: int
    caller_ip: int
    caller_fn: str


@dataclass
class ThreadFailure(HarkSerialisable):
    thread: int
    error_msg: str
    stacktrace: List[StackTraceItem]
