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
import warnings
from typing import List, Tuple

from ..machine import future as fut
from ..machine.controller import Controller, ControllerError
from . import ddb_model as db
from .ddb_model import (
    AREC,
    FUTURE,
    META,
    PEVENTS,
    PLOGS,
    STATE,
    STDOUT,
    PLUGINS_HASH_KEY,
)

try:
    from ..machine.executable import Executable
    from ..machine.probe import ProbeEvent, ProbeLog
    from ..machine.state import State
    from ..machine.stdout_item import StdoutItem
except ModuleNotFoundError:
    warnings.warn(
        "Could not import some components - controller won't be fully functional."
    )


LOG = logging.getLogger(__name__)


class DataController(Controller):
    supports_plugins = True

    @classmethod
    def with_new_session(cls):
        """Create a data controller for a new session"""
        base_session = db.init_base_session()
        this_session = db.new_session()
        LOG.info("Created new session, %s", this_session.session_id)
        return cls(this_session, base_session)

    @classmethod
    def with_session_id(cls, session_id: str, db_cls=db.SessionItem):
        try:
            base_session = db.init_base_session()
            this_session = db_cls.get(session_id, META)
        except db_cls.DoesNotExist as exc:
            raise ControllerError("Session does not exist") from exc
        LOG.info("Reloaded session %s", session_id)
        return cls(this_session, base_session, db_cls=db_cls)

    def __init__(self, this_session, base_session, db_cls=db.SessionItem):
        self.SI = db_cls
        self.session_id = this_session.session_id
        if base_session.meta.exe:
            self.executable = Executable.deserialise(base_session.meta.exe)
        elif this_session.meta.exe:
            self.executable = Executable.deserialise(this_session.meta.exe)
        else:
            self.executable = None
            # It's allowed to initialise a controller with no executable, as
            # long as the user calls set_executable before creating a machine.

    def _qry(self, group, item_id=None):
        """Retrieve the specified group:item_id"""
        _key = f"{group}:{item_id}" if item_id is not None else group
        try:
            return self.SI.get(self.session_id, _key, consistent_read=True)
        except self.SI.DoesNotExist as exc:
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
        s = self._qry(META)
        s.meta.exe = exe.serialise()
        s.save()
        LOG.info("Updated session code")

    def set_entrypoint(self, fn_name: str):
        s = self._qry(META)
        s.meta.entrypoint = fn_name
        s.save()

    ## Threads

    def new_thread(self) -> int:
        """Create a new thread, returning the thead ID"""
        with self._lock_item(META):
            s = self._qry(META)
            vmid = s.meta.num_threads
            s.meta.num_threads += 1
            s.meta.stopped.append(False)
            s.save()

        db.new_session_item(self.session_id, f"{STATE}:{vmid}", state=State([])).save()
        db.new_session_item(
            self.session_id, f"{FUTURE}:{vmid}", future=fut.Future()
        ).save()
        return vmid

    def get_thread_ids(self) -> List[int]:
        """Get a list of thread IDs in this session"""
        s = self._qry(META)
        return list(range(s.meta.num_threads))

    def get_top_level_future(self):
        return self.get_future(0)

    def is_top_level(self, vmid):
        return vmid == 0

    def all_stopped(self):
        s = self._qry(META)
        return all(s.meta.stopped)

    def set_stopped(self, vmid, stopped: bool):
        with self._lock_item(META):
            s = self._qry(META)
            s.meta.stopped[vmid] = stopped
            s.save()

    def set_state(self, vmid, state):
        # NOTE: no locking required, no inter-thread state access allowed
        s = self._qry(STATE, vmid)
        s.state = state
        s.save()

    def get_state(self, vmid):
        return self._qry(STATE, vmid).state

    ## controller properties

    @property
    def broken(self):
        s = self._qry(META)
        return s.meta.broken

    @broken.setter
    def broken(self, value):
        try:
            with self._lock_item(META):
                s = self._qry(META)
                s.meta.broken = True
                s.save()
        except db.LockTimeout:
            # If a thread dies while updating META, this will timeout. However,
            # in that case, broken is True and we *should* ignore the lock and
            # carry on. If it's broken, the lock doesn't matter anyway.
            # Hopefully this isn't a genuine race condition.
            if value:
                s = self._qry(META)
                s.meta.broken = True
                s.save()
            else:
                raise

    @property
    def result(self):
        s = self._qry(META)
        return s.meta.result

    @result.setter
    def result(self, value):
        with self._lock_item(META):
            s = self._qry(META)
            s.meta.result = value
            s.save()

    ## arecs

    def new_arec(self):
        with self._lock_item(META):
            s = self._qry(META)
            ptr = s.meta.num_arecs
            s.meta.num_arecs += 1
            s.save()
        return ptr

    def set_arec(self, ptr, rec):
        try:
            s = self._qry(AREC, ptr)
            s.arec = rec
        except ControllerError:
            s = db.new_session_item(self.session_id, f"{AREC}:{ptr}", arec=rec)
        s.save()

    def get_arec(self, ptr):
        return self._qry(AREC, ptr).arec

    def increment_ref(self, ptr):
        s = self._qry(AREC, ptr)
        s.update(actions=[self.SI.arec.ref_count.set(self.SI.arec.ref_count + 1)])

    def decrement_ref(self, ptr):
        s = self._qry(AREC, ptr)
        s.update(actions=[self.SI.arec.ref_count.set(self.SI.arec.ref_count - 1)])
        return s.arec

    def delete_arec(self, ptr):
        s = self._qry(AREC, ptr)
        s.arec.deleted = True

    def lock_arec(self, ptr):
        return self._lock_item(AREC, ptr)

    ## probes

    def set_probe_data(self, vmid, probe):
        # FIXME - 400k limit on item size is quite easy to break with events and
        # logs.
        events = [item.serialise() for item in probe.events]
        s = self._qry(PEVENTS)
        s.update(actions=[self.SI.pevents.set(self.SI.pevents.append(events))])

        logs = [item.serialise() for item in probe.logs]
        s = self._qry(PLOGS)
        s.update(actions=[self.SI.plogs.set(self.SI.plogs.append(logs))])

    def get_probe_logs(self):
        s = self._qry(PLOGS)
        return [ProbeLog.deserialise(item) for item in s.plogs]

    def get_probe_events(self):
        s = self._qry(PEVENTS)
        return [ProbeEvent.deserialise(item) for item in s.pevents]

    ## futures

    def get_future(self, vmid):
        s = self._qry(FUTURE, vmid)
        return s.future

    def set_future(self, vmid, future: fut.Future):
        s = self._qry(FUTURE, vmid)
        s.future = future
        s.save()

    def add_continuation(self, fut_ptr, vmid):
        s = self._qry(FUTURE, fut_ptr)
        s.update(
            actions=[
                self.SI.future.continuations.set(
                    self.SI.future.continuations.append([vmid])
                )
            ]
        )

    def set_future_chain(self, fut_ptr, chain):
        s = self._qry(FUTURE, fut_ptr)
        s.update(actions=[self.SI.future.chain.set(chain)])

    def lock_future(self, ptr):
        return self._lock_item(FUTURE, ptr)

    ## stdout

    def get_stdout(self):
        s = self._qry(STDOUT)
        return [StdoutItem.deserialise(item) for item in s.stdout]

    def write_stdout(self, item):
        # Avoid empty strings (DynamoDB can't handle them)
        if item.text:
            sys.stdout.write(item.text)
            s = self._qry(STDOUT)
            s.update(
                actions=[self.SI.stdout.set(self.SI.stdout.append([item.serialise()]))]
            )

    @property  # Legacy. TODO: remove
    def stdout(self):
        return self.get_stdout()

    ## plugin API

    def supports_plugin(self, name: str):
        # TODO
        return True

    def add_plugin_future(self, plugin_name: str, plugin_value_id: str) -> str:
        """Add a special kind of future which is resolved by a plugin"""
        future_id = f"{plugin_name}:{plugin_value_id}"
        # Create a pointer to this session for the plugin to resume
        db.new_session_item(
            PLUGINS_HASH_KEY, future_id, plugin_future_session=self.session_id,
        ).save()
        # Create the actual future
        db.new_session_item(
            self.session_id, f"{FUTURE}:{future_id}", future=fut.Future(),
        ).save()
        return future_id

    @classmethod
    def find_plugin_future(
        cls, plugin_name: str, plugin_value_id: str
    ) -> Tuple[str, str]:
        future_id = f"{plugin_name}:{plugin_value_id}"
        try:
            s = cls.SI.get(PLUGINS_HASH_KEY, future_id)
        except cls.SI.DoesNotExist as exc:
            raise ControllerError("Future does not exist") from exc
        return (s.plugin_future_session, future_id)
