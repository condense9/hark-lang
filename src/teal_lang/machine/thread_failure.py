"""ThreadFailure class"""
import time
from dataclasses import asdict, dataclass
from typing import List

from .teal_serialisable import TealSerialisable


@dataclass
class StackTraceItem(TealSerialisable):
    caller_thread: int
    caller_ip: int
    caller_fn: str


@dataclass
class ThreadFailure(TealSerialisable):
    thread: int
    error_msg: str
    stacktrace: List[StackTraceItem]
