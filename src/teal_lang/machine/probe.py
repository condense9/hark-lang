"""Machine Probe"""

from dataclasses import dataclass
import time

from .teal_serialisable import TealSerialisable


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


class Probe:
    """A small interface for storing machine logs and events"""

    def __init__(self, vmid):
        self.vmid = vmid
        self.logs = []
        self.events = []

    def event(self, etype: str, **data):
        self.events.append(
            ProbeEvent(thread=self.vmid, time=time.time(), event=etype, data=data)
        )

    def log(self, text):
        self.logs.append(ProbeLog(thread=self.vmid, time=time.time(), text=text))
