"""DB interaction layer for AWS"""

import base64
import dataclasses
import logging
import os
import threading
import time
import uuid
from contextlib import AbstractContextManager
from datetime import datetime
from typing import List

from botocore.exceptions import ClientError
from pynamodb.attributes import (
    BooleanAttribute,
    JSONAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.exceptions import UpdateError, TableDoesNotExist
from pynamodb.models import Model

from ..exceptions import TealError
from ..machine.arec import ActivationRecord
from ..machine.future import Future
from ..machine.state import State

LOG = logging.getLogger(__name__)


# Make it harder to accidentally use real AWS resources:
if "DYNAMODB_ENDPOINT" not in os.environ and "USE_LIVE_AWS" not in os.environ:
    raise RuntimeError("One of DYNAMODB_ENDPOINT or USE_LIVE_AWS must be set!")

# Get the session item time-to-live
ITEM_TTL = int(os.getenv("TEAL_SESSION_TTL", 0))  # TTL=0 means don't expire

# Default Teal sessions table name
DEFAULT_TABLE_NAME = "TealSessions"

# pseudo-sessions
BASE_SESSION_HASH_KEY = "base"
PLUGINS_HASH_KEY = "plugins"

# DDB item type prefix constants
FUTURE = "future"
META = "meta"
AREC = "arec"
STATE = "state"
PLOGS = "plogs"
PEVENTS = "pevents"
STDOUT = "stdout"


class FutureAttribute(MapAttribute):
    resolved = BooleanAttribute(default=False)
    continuations = ListAttribute(default=list)
    chain = NumberAttribute(null=True)
    value = JSONAttribute(null=True)

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return Future.deserialise(super().deserialize(value).as_dict())


class ARecAttribute(MapAttribute):
    ref_count = NumberAttribute()
    function = ListAttribute(null=True)
    dynamic_chain = NumberAttribute(null=True)
    vmid = NumberAttribute(null=True)
    call_site = NumberAttribute(null=True)
    bindings = MapAttribute(default=dict)
    deleted = BooleanAttribute(default=False)

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return ActivationRecord.deserialise(super().deserialize(value).as_dict())


class MetaAttribute(MapAttribute):
    num_threads = NumberAttribute(default=0)
    num_arecs = NumberAttribute(default=0)
    entrypoint = UnicodeAttribute(null=True)
    stopped = ListAttribute(default=list)
    exe = MapAttribute(null=True)
    result = JSONAttribute(null=True)
    broken = BooleanAttribute(default=False)


class TealDataAttribute(JSONAttribute):
    """General purpose JSON-able Teal type"""

    value_cls = None

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return self.value_cls.deserialise(super().deserialize(value))


class StateAttribute(TealDataAttribute):
    value_cls = State


class SessionItem(Model):
    class Meta:
        table_name = os.environ.get("DYNAMODB_TABLE", DEFAULT_TABLE_NAME)
        host = os.environ.get("DYNAMODB_ENDPOINT", None)
        region = os.environ.get("AWS_DEFAULT_REGION", None)

    session_id = UnicodeAttribute(hash_key=True)
    item_id = UnicodeAttribute(range_key=True)
    locked = BooleanAttribute(default=False)
    # TODO create LSI on created_at
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    expires_on = NumberAttribute()

    # Only one of these items should actually be set, determined by the item_id
    new_session_record = UnicodeAttribute(null=True)
    plugin_future_session = UnicodeAttribute(null=True)
    meta = MetaAttribute(null=True)
    stdout = ListAttribute(null=True)
    plogs = ListAttribute(null=True)
    pevents = ListAttribute(null=True)
    arec = ARecAttribute(null=True)
    future = FutureAttribute(null=True)
    state = StateAttribute(null=True)


###


def init_base_session() -> SessionItem:
    LOG.info("DB %s (%s)", SessionItem.Meta.host, SessionItem.Meta.region)
    LOG.info("DB table %s", SessionItem.Meta.table_name)
    try:
        s = SessionItem.get(BASE_SESSION_HASH_KEY, META)
    except SessionItem.DoesNotExist as exc:
        LOG.info("Creating base session")
        s = SessionItem(
            BASE_SESSION_HASH_KEY,
            META,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_on=0,  # ie, don't expire
            meta=MetaAttribute(),
        )
        s.save()
    return s


def set_base_exe(exe):
    base_session = SessionItem.get(BASE_SESSION_HASH_KEY, META)
    base_session.meta.exe = exe.serialise()
    base_session.save()


def new_session_item(sid, item_id, **extra) -> SessionItem:
    """Helper to make a new item with given session_id, item_id and extra data

    Sets the housekeeping fields (TTL, created_at, expires_on, etc).
    """
    return SessionItem(
        session_id=sid,
        item_id=item_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        expires_on=int(ITEM_TTL + time.time()) if ITEM_TTL else 0,
        **extra,
    )


def new_session() -> SessionItem:
    """Create a new session, returning the 'meta' item for it"""
    base_session = SessionItem.get(BASE_SESSION_HASH_KEY, META)
    sid = str(uuid.uuid4())

    s = new_session_item(sid, META, meta=MetaAttribute())
    s.save()
    # Create the empty placeholders for the collections
    new_session_item(sid, PLOGS, plogs=[]).save()
    new_session_item(sid, PEVENTS, pevents=[]).save()
    new_session_item(sid, STDOUT, stdout=[]).save()

    # Record the new session for cheap retrieval later
    SessionItem(
        session_id=BASE_SESSION_HASH_KEY,
        item_id=str(s.created_at),  # for sorting by created_at
        created_at=datetime.now(),
        updated_at=datetime.now(),
        expires_on=int(ITEM_TTL + time.time()) if ITEM_TTL else 0,
        new_session_record=sid,
    ).save()

    return s


def list_sessions(cls=SessionItem) -> List[str]:
    """List existing session IDs"""
    # TODO pagination
    # https://pynamodb.readthedocs.io/en/latest/api.html?highlight=scan#pynamodb.models.Model.query
    try:
        return [
            s.new_session_record
            for s in cls.query(
                BASE_SESSION_HASH_KEY, scan_index_forward=False, limit=10
            )
            if s.new_session_record
        ]
    except TableDoesNotExist:
        return []


###


def try_lock(session, thread_lock) -> bool:
    """Try to acquire a lock on an item, returning True if successful"""
    if not thread_lock.acquire(blocking=False):
        return False

    try:
        session.update(
            [SessionItem.locked.set(True)], condition=(SessionItem.locked == False)
        )
        return True

    except UpdateError as e:
        thread_lock.release()
        if isinstance(e.cause, ClientError):
            code = e.cause.response["Error"].get("Code")
            LOG.info("Failed to lock: %s", code)
            if code == "ConditionalCheckFailedException":
                return False
            raise
        raise


class LockTimeout(TealError):
    """Timeout trying to lock item"""


class SessionLocker(AbstractContextManager):
    """Lock an item for modification (re-entrant for chain_resolve)

    https://docs.python.org/3/library/contextlib.html#reentrant-context-managers
    """

    def __init__(self, session, timeout=2.0):
        self.session = session
        self.timeout = timeout
        self._thread_lock = threading.Lock()
        self.lock_count = {}

    def __enter__(self):
        tid = threading.get_native_id()

        # re-lock if this thread has already got one lock
        if self._thread_lock.locked() and self.lock_count.get(tid, 0) > 0:
            t = time.time() % 1000.0
            self.lock_count[tid] += 1
            LOG.debug(f"{t:.3f} :: acquire re-entrant %d", self.lock_count[tid])
            return

        start = time.time()
        while not try_lock(self.session, self._thread_lock):
            time.sleep(0.01)
            if time.time() - start > self.timeout:
                t = time.time() % 1000.0
                LOG.debug(f"{t:.3f} :: Timeout getting lock")
                raise LockTimeout

        self.lock_count[tid] = 1

        t = time.time() % 1000.0
        LOG.debug(f"{t:.3f} :: Thread {tid} Locked %s", self.session)

    def __exit__(self, *exc):
        """Release the lock"""
        tid = threading.get_native_id()

        if self._thread_lock.locked() and self.lock_count.get(tid, 0) > 1:
            self.lock_count[tid] -= 1
            t = time.time() % 1000.0
            LOG.debug(f"{t:.3f} :: release re-entrant %d", self.lock_count[tid])
            return

        self.lock_count[tid] -= 1
        assert self.lock_count[tid] == 0

        LOG.debug(f"%d :: Releasing %s...", time.time() % 1000.0, self.session)
        self.session.update(
            [SessionItem.locked.set(False)], condition=(SessionItem.locked == True)
        )
        self._thread_lock.release()
