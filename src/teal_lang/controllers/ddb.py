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
import time

from ..machine import future as fut
from ..machine.controller import Controller
from ..machine.executable import Executable
from . import ddb_model as db
from ..machine.probe import Probe
from ..machine.state import State

LOG = logging.getLogger(__name__)

SI = db.SessionItem


class DataController(Controller):
    def __init__(self, session_meta: str):
        self.sid = session_meta.session_id
        self._locks = {}
        if session_meta.meta.exe:
            self.executable = Executable.deserialise(session_meta.meta.exe)

    def qry(self, group, item_id=None):
        _key = f"{group}:{item_id}" if item_id is not None else group
        return SI.get(self.sid, _key)

    def lock_item(self, group, item_id=None):
        lock_key = (group, item_id)
        if lock_key not in self._locks:
            item = self.qry(group, item_id)
            self._locks[lock_key] = db.SessionLocker(item)
        return self._locks[lock_key]

    def set_executable(self, exe):
        self.executable = exe
        s = self.qry("meta")
        s.meta.exe = exe.serialise()
        s.save()

    def new_thread(self):
        with self.lock_item("meta"):
            s = self.qry("meta")
            vmid = s.meta.num_threads
            s.meta.num_threads += 1
            s.meta.stopped.append(False)
            s.save()

        db.new_session_item(self.sid, f"state:{vmid}", state=State([])).save()
        db.new_session_item(self.sid, f"future:{vmid}", future=fut.Future()).save()
        return vmid

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        s = self.qry("meta")
        return all(s.meta.stopped)

    def set_stopped(self, vmid, stopped: bool):
        with self.lock_item("meta"):
            s = self.qry("meta")
            s.meta.stopped[vmid] = stopped
            s.save()

    ##

    @property
    def broken(self):
        s = self.qry("meta")
        return s.meta.broken

    @broken.setter
    def broken(self, value):
        s = self.qry("meta")
        s.meta.broken = True
        s.save()

    @property
    def result(self):
        s = self.qry("meta")
        return s.meta.result

    @result.setter
    def result(self, value):
        s = self.qry("meta")
        s.meta.result = value
        s.save()

    ## arecs

    def new_arec(self):
        with self.lock_item("meta"):
            s = self.qry("meta")
            ptr = s.meta.num_arecs
            s.meta.num_arecs += 1
            s.save()
        return ptr

    def set_arec(self, ptr, rec):
        try:
            s = self.qry("arec", ptr)
            s.arec = rec
        except SI.DoesNotExist:
            s = db.new_session_item(self.sid, f"arec:{ptr}", arec=rec)
        s.save()

    def get_arec(self, ptr):
        return self.qry("arec", ptr).arec

    def increment_ref(self, ptr):
        s = self.qry("arec", ptr)
        s.update(actions=[SI.arec.ref_count.set(SI.arec.ref_count + 1)])

    def decrement_ref(self, ptr):
        s = self.qry("arec", ptr)
        s.update(actions=[SI.arec.ref_count.set(SI.arec.ref_count - 1)])
        return s.arec

    def delete_arec(self, ptr):
        s = self.qry("arec", ptr)
        s.arec.deleted = True

    def lock_arec(self, ptr):
        return self.lock_item("arec", ptr)

    ## thread

    def set_state(self, vmid, state):
        s = self.qry("state", vmid)
        s.state = state
        s.save()

    def get_state(self, vmid):
        return self.qry("state", vmid).state

    def get_probe(self, vmid):
        return Probe()

    def set_probe(self, vmid, probe):
        events = [
            db.ProbeEvent(
                thread=vmid, time=e["time"], event=e["event"], data=e["data"],
            )
            for e in probe.serialised_events
        ]
        s = self.qry("pevents")
        s.update(actions=[SI.pevents.set(SI.pevents.append(events))])

        logs = [
            db.ProbeLog(thread=vmid, time=l["time"], log=l["log"]) for l in probe.logs
        ]
        s = self.qry("plogs")
        s.update(actions=[SI.plogs.set(SI.plogs.append(logs))])

    def get_probe_logs(self):
        s = self.qry("plogs")
        return s.plogs

    ##

    def get_future(self, vmid):
        s = self.qry("future", vmid)
        return s.future

    def set_future(self, vmid, future: fut.Future):
        s = self.qry("future", vmid)
        s.future = future
        s.save()

    def add_continuation(self, fut_ptr, vmid):
        s = self.qry("future", fut_ptr)
        s.update(
            actions=[
                SI.future.continuations.set(SI.future.continuations.append([vmid]))
            ]
        )

    def set_future_chain(self, fut_ptr, chain):
        s = self.qry("future", fut_ptr)
        s.update(actions=[SI.future.chain.set(chain)])

    def lock_future(self, ptr):
        return self.lock_item("future", ptr)

    ## misc

    @property
    def machines(self):
        return list(self.session.machines)

    @property
    def stdout(self):
        s = self.qry("stdout")
        return s.stdout

    def write_stdout(self, vmid, value: str):
        # don't use isinstance - it must be an actual str
        if type(value) != str:
            raise ValueError(f"{value} ({type(value)}) is not str")

        # Avoid empty strings (they break dynamodb)
        if value:
            s = self.qry("stdout")
            out = db.Stdout(thread=vmid, time=time.time(), log=value)
            s.update(actions=[SI.stdout.set(SI.stdout.append([out]))])
