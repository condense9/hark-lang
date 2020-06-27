"""Local Implementation"""
import logging
import sys
import time
import threading
from functools import singledispatchmethod
from typing import List

from ..machine import future as fut
from ..machine.arec import ARecPtr
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
        self._probe_events = []
        self._arecs = {}
        self._lock = threading.RLock()
        self.executable = None
        self.stdout = []  # shared standard output
        self.broken = False
        self.result = None

    def set_executable(self, exe):
        self.executable = exe

    def set_entrypoint(self, fn_name: str):
        pass  # N/A for local

    ## Threads

    def new_thread(self):
        vmid = self._machine_idx
        self._machine_idx += 1
        return vmid

    def get_thread_ids(self) -> List[int]:
        return list(range(self._machine_idx))

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        return all(self._machine_stopped.values())

    def set_stopped(self, vmid, stopped: bool):
        self._machine_stopped[vmid] = stopped

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def set_state(self, vmid, state):
        self._machine_state[vmid] = state

    ## arecs

    def new_arec(self) -> ARecPtr:
        ptr = ARecPtr(self._arec_idx)
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
        self._arecs[ptr].deleted = True

    def lock_arec(self, _):
        return self._lock

    ## probes

    def set_probe_data(self, vmid, probe):
        self._probe_logs.extend(probe.logs)
        self._probe_events.extend(probe.events)

    def get_probe_logs(self):
        return list(self._probe_logs)

    def get_probe_events(self):
        return list(self._probe_events)

    ## futures

    def get_future(self, val):
        if not isinstance(val, int):
            raise TypeError(val)
        return self._machine_future[val]

    def set_future(self, vmid, future: fut.Future):
        self._machine_future[vmid] = future

    def add_continuation(self, fut_ptr, vmid):
        self._machine_future[fut_ptr].continuations.append(vmid)

    def set_future_chain(self, fut_ptr, chain):
        self._machine_future[fut_ptr].chain = chain

    def lock_future(self, _):
        # Shared thread lock
        return self._lock

    ## stdout

    def get_stdout(self):
        return list(self.stdout)

    def write_stdout(self, item):
        # Print to real stdout at the same time. TODO maybe make this behaviour
        # configurable.
        sys.stdout.write(item.text)
        self.stdout.append(item)
