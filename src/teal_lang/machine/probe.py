"""Machine Probe"""

from dataclasses import dataclass

from .types import TlType
from .teal_serialisable import TealSerialisable, now_str


@dataclass(frozen=True)
class ProbeLog(TealSerialisable):
    thread: int
    time: int
    text: str


@dataclass(frozen=True)
class ProbeEvent(TealSerialisable):
    thread: int
    time: int
    event: str
    data: dict

    # TODO deserialise?


class Probe:
    """A small interface for storing machine logs and events"""

    def __init__(self, vmid):
        self.vmid = vmid
        self.logs = []
        self.events = []

    def event(self, etype: str, **data):
        e = ProbeEvent(thread=self.vmid, time=now_str(), event=etype, data=data)
        self.events.append(e)

    def log(self, text):
        l = ProbeLog(thread=self.vmid, time=now_str(), text=text)
        self.logs.append(l)
