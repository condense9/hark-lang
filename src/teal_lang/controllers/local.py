"""Local Implementation"""
import logging
import sys
import time
import threading
from functools import singledispatchmethod

from ..machine import future as fut
from ..machine.probe import Probe
from ..machine.controller import Controller

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class DataController(Controller):
    def __init__(self):
        self._machine_future = {}
        self._machine_state = {}
        self._machine_stopped = {}
        self._machine_idx = 0  # always increasing machine counter
        self._arec_idx = 0  # always increasing arec counter
        self._probe_logs = []
        self._arecs = {}
        self._lock = threading.RLock()
        self.executable = None
        self.stdout = []  # shared standard output
        self.broken = False
        self.result = None

    def set_executable(self, exe):
        self.executable = exe

    def new_thread(self):
        vmid = self._machine_idx
        self._machine_idx += 1
        return vmid

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        return all(self._machine_stopped.values())

    def set_stopped(self, vmid, stopped: bool):
        self._machine_stopped[vmid] = stopped

    ## arecs

    def new_arec(self):
        ptr = self._arec_idx
        self._arec_idx += 1
        return ptr

    def set_arec(self, ptr, rec):
        self._arecs[ptr] = rec

    def get_arec(self, ptr):
        return self._arecs[ptr]

    def increment_ref(self, ptr):
        self._arecs[ptr].ref_count += 1
        return self._arecs[ptr].ref_count

    def decrement_ref(self, ptr):
        self._arecs[ptr].ref_count -= 1
        return self._arecs[ptr]

    def delete_arec(self, ptr):
        self._arecs.pop(ptr)

    def lock_arec(self, _):
        return self._lock

    ## thread

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def set_state(self, vmid, state):
        self._machine_state[vmid] = state

    def get_probe(self, vmid):
        return Probe()

    def set_probe(self, vmid, probe):
        self._probe_logs.extend(
            dict(thread=vmid, time=l["time"], log=l["log"]) for l in probe.logs
        )
        # TODO probe events

    ##

    def set_future(self, vmid, future: fut.Future):
        self._machine_future[vmid] = future

    def get_future(self, val):
        if not isinstance(val, int):
            raise TypeError(val)
        return self._machine_future[val]

    def add_continuation(self, fut_ptr, vmid):
        self._machine_future[fut_ptr].continuations.append(vmid)

    def set_future_chain(self, fut_ptr, chain):
        self._machine_future[fut_ptr].chain = chain

    def lock_future(self, _):
        return self._lock

    ##

    @property
    def machines(self):
        return list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]

    def write_stdout(self, vmid, value: str):
        # don't use isinstance - it must be an actual str
        if type(value) != str:
            raise ValueError(f"{value} ({type(value)}) is not str")
        # Print to real stdout at the same time. TODO maybe make this behaviour
        # configurable.
        sys.stdout.write(value)
        self.stdout.append(dict(thread=vmid, time=time.time(), log=value))

    def get_probe_logs(self):
        return self._probe_logs
