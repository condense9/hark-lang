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
import functools
import logging
import sys
import time
from typing import List

from ..machine import future as fut
from ..machine.controller import Controller, ControllerError
from ..machine.executable import Executable
from ..machine.probe import ProbeEvent, ProbeLog
from ..machine.state import State
from ..machine.stdout_item import StdoutItem
from . import ddb_model as db

LOG = logging.getLogger(__name__)

# Alias
SI = db.SessionItem


class DataController(Controller):
    @classmethod
    def with_new_session(cls):
        """Create a data controller for a new session"""
        db.init_base_session()
        return cls(db.new_session())

    @classmethod
    def with_session_id(cls, session_id: str):
        try:
            session = SI.get(session_id, "meta")
        except SI.DoesNotExist as exc:
            raise ControllerError("Session does not exist") from exc
        return cls(session)

    def __init__(self, session_meta):
        self.session_id = session_meta.session_id
        if session_meta.meta.exe:
            self.executable = Executable.deserialise(session_meta.meta.exe)
        else:
            self.executable = None

    def _qry(self, group, item_id=None):
        """Retrieve the specified group:item_id"""
        _key = f"{group}:{item_id}" if item_id is not None else group
        try:
            return SI.get(self.session_id, _key)
        except SI.DoesNotExist as exc:
            raise ControllerError(
                f"Item {_key} does not exist in {self.session_id}"
            ) from exc

    @functools.lru_cache
    def _lock_item(self, group: str, item_id=None) -> db.SessionLocker:
        """Get a context manager that locks the specified group:item_id"""
        item = self._qry(group, item_id)
        return db.SessionLocker(item)

    def set_executable(self, exe):
        self.executable = exe
        s = self._qry("meta")
        s.meta.exe = exe.serialise()
        try:
            s.save()
        except SI.UpdateError as exc:
            raise ControllerError("Could not update session executable") from exc
        LOG.info("Updated session code")

    def set_entrypoint(self, fn_name: str):
        s = self._qry("meta")
        s.meta.entrypoint = fn_name
        try:
            s.save()
        except SI.UpdateError as exc:
            raise ControllerError from exc

    ## Threads

    def new_thread(self) -> int:
        """Create a new thread, returning the thead ID"""
        with self._lock_item("meta"):
            s = self._qry("meta")
            vmid = s.meta.num_threads
            s.meta.num_threads += 1
            s.meta.stopped.append(False)
            s.save()

        db.new_session_item(self.session_id, f"state:{vmid}", state=State([])).save()
        db.new_session_item(
            self.session_id, f"future:{vmid}", future=fut.Future()
        ).save()
        return vmid

    def get_thread_ids(self) -> List[int]:
        """Get a list of thread IDs in this session"""
        s = self._qry("meta")
        return list(range(s.meta.num_threads))

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        s = self._qry("meta")
        return all(s.meta.stopped)

    def set_stopped(self, vmid, stopped: bool):
        with self._lock_item("meta"):
            s = self._qry("meta")
            s.meta.stopped[vmid] = stopped
            s.save()

    def set_state(self, vmid, state):
        # NOTE: no locking required, no inter-thread state access allowed
        s = self._qry("state", vmid)
        s.state = state
        s.save()

    def get_state(self, vmid):
        return self._qry("state", vmid).state

    ## controller properties

    @property
    def broken(self):
        s = self._qry("meta")
        return s.meta.broken

    @broken.setter
    def broken(self, value):
        with self._lock_item("meta"):
            s = self._qry("meta")
            s.meta.broken = True
            s.save()

    @property
    def result(self):
        s = self._qry("meta")
        return s.meta.result

    @result.setter
    def result(self, value):
        with self._lock_item("meta"):
            s = self._qry("meta")
            s.meta.result = value
            s.save()

    ## arecs

    def new_arec(self):
        with self._lock_item("meta"):
            s = self._qry("meta")
            ptr = s.meta.num_arecs
            s.meta.num_arecs += 1
            s.save()
        return ptr

    def set_arec(self, ptr, rec):
        try:
            s = self._qry("arec", ptr)
            s.arec = rec
        except ControllerError:
            s = db.new_session_item(self.session_id, f"arec:{ptr}", arec=rec)
        s.save()

    def get_arec(self, ptr):
        return self._qry("arec", ptr).arec

    def increment_ref(self, ptr):
        s = self._qry("arec", ptr)
        s.update(actions=[SI.arec.ref_count.set(SI.arec.ref_count + 1)])

    def decrement_ref(self, ptr):
        s = self._qry("arec", ptr)
        s.update(actions=[SI.arec.ref_count.set(SI.arec.ref_count - 1)])
        return s.arec

    def delete_arec(self, ptr):
        s = self._qry("arec", ptr)
        s.arec.deleted = True

    def lock_arec(self, ptr):
        return self._lock_item("arec", ptr)

    ## probes

    def set_probe_data(self, vmid, probe):
        events = [item.serialise() for item in probe.events]
        s = self._qry("pevents")
        s.update(actions=[SI.pevents.set(SI.pevents.append(events))])

        logs = [item.serialise() for item in probe.logs]
        s = self._qry("plogs")
        s.update(actions=[SI.plogs.set(SI.plogs.append(logs))])

    def get_probe_logs(self):
        s = self._qry("plogs")
        return [ProbeLog.deserialise(item) for item in s.plogs]

    def get_probe_events(self):
        s = self._qry("pevents")
        return [ProbeEvent.deserialise(item) for item in s.pevents]

    ## futures

    def get_future(self, vmid):
        s = self._qry("future", vmid)
        return s.future

    def set_future(self, vmid, future: fut.Future):
        s = self._qry("future", vmid)
        s.future = future
        s.save()

    def add_continuation(self, fut_ptr, vmid):
        s = self._qry("future", fut_ptr)
        s.update(
            actions=[
                SI.future.continuations.set(SI.future.continuations.append([vmid]))
            ]
        )

    def set_future_chain(self, fut_ptr, chain):
        s = self._qry("future", fut_ptr)
        s.update(actions=[SI.future.chain.set(chain)])

    def lock_future(self, ptr):
        return self._lock_item("future", ptr)

    ## stdout

    def get_stdout(self):
        s = self._qry("stdout")
        return [StdoutItem.deserialise(item) for item in s.stdout]

    def write_stdout(self, item):
        # Avoid empty strings (DynamoDB can't handle them)
        if item.text:
            sys.stdout.write(item.text)
            s = self._qry("stdout")
            s.update(actions=[SI.stdout.set(SI.stdout.append([item.serialise()]))])

    @property  # Legacy. TODO: remove
    def stdout(self):
        return self.get_stdout()
