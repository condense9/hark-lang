"""AWS DynamoDB backed storage

In AWS, there will be one Machine executing in the current context, and others
executing elsewhere, as part of the same "session". There is one Controller per
session.

Data per session:
- futures (resolved, value, chain, continuations - machine, offset)
- machines (probe logs, state - ip, stopped flag, stacks, and bindings)

Data exchange points:
- machine forks (State of new machine set to point at the fork IP)
- machine waits on future (continuation added to that future)
- machine checks whether future is resolved
- future resolves (must refresh list of continuations)
- top level machine finishes (Controller sets session result)
- machine stops (upload the State)
- machine continues (download the State)
"""

import logging

from ..machine import future as fut
from ..machine.controller import Controller
from ..machine.executable import Executable
from . import ddb_model as db
from ..machine.probe import Probe

LOG = logging.getLogger(__name__)


class DataController(Controller):
    def __init__(self, session):
        self.session = session
        if session.executable:
            self.executable = Executable.deserialise(session.executable)
        self._lock = db.SessionLocker(session)

    def set_executable(self, exe):
        self.executable = exe
        self.session.executable = exe.serialise()
        self.session.save()

    def new_thread(self):
        with self._lock:
            vmid = db.new_machine(self.session, [])
        return vmid

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        self.session.refresh()
        return all(self.session.thread_stopped)

    ##

    @property
    def result(self):
        return self.session.result

    @result.setter
    def result(self, value):
        self.session.result = value

    ## arecs

    def new_arec(self):
        with self._lock:
            ptr = self.session.num_arecs
            self.session.num_arecs += 1
            self.session.arecs.append("empty")
        return ptr

    def set_arec(self, ptr, rec):
        with self._lock:
            self.session.arecs[ptr] = rec.serialise()

    def get_arec(self, ptr):
        self.session.refresh()
        return self.session.arecs[ptr].deserialise()

    def increment_ref(self, ptr):
        self.session.arecs[ptr]["ref_count"] += 1
        return self.session.arecs[ptr]["ref_count"]

    def decrement_ref(self, ptr):
        self.session.arecs[ptr]["ref_count"] -= 1
        return self.session.arecs[ptr]["ref_count"]

    def delete_arec(self, ptr):
        # just replace with a tag to save space - can't break list order
        self.session.arecs[ptr] = "garbage"

    def lock_arec(self, _):
        return self._lock

    ## thread

    def get_state(self, vmid):
        # refresh session?
        return self.session.machines[vmid].state

    def set_state(self, vmid, state):
        # refresh session?
        with self._lock:
            self.session.machines[vmid].state = state

    def get_probe(self, vmid):
        # TODO - machine-specific probes?
        return Probe()

    def set_probe(self, vmid, probe):
        # refresh session?
        self.session.machines[vmid].probe_events.append(probe.serialised_events)
        self.session.machines[vmid].probe_logs.append(probe.logs)

    def set_stopped(self, vmid, stopped: bool):
        self.session.thread_stopped[vmid] = stopped

    ##

    def get_future(self, vmid):
        f = self.session.machines[vmid].future
        return f

    def set_future(self, vmid, future: fut.Future):
        with self._lock:
            self.session.machines[vmid].future = future

    def add_continuation(self, fut_ptr, vmid):
        self.get_future(fut_ptr.vmid).continuations.append(vmid)

    def lock_future(self, _):
        return self._lock

    ## misc

    @property
    def machines(self):
        return list(self.session.machines)

    @property
    def probes(self):
        return [Probe.with_logs(m.probe_logs) for m in self.session.machines]

    @property
    def stdout(self):
        return list(self.session.stdout)

    def write_stdout(self, value: str):
        # don't use isinstance - it must be an actual str
        if type(value) != str:
            raise ValueError(f"{value} ({type(value)}) is not str")

        # Avoid empty strings (they break dynamodb)
        if value:
            with self._lock:
                self.session.stdout.append(value)
