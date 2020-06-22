"""DB interaction layer for AWS"""

import base64
import dataclasses
import logging
import os
import threading
import time
import uuid
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime

from botocore.exceptions import ClientError
from pynamodb.attributes import (
    Attribute,
    BinaryAttribute,
    BooleanAttribute,
    JSONAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
    VersionAttribute,
)
from pynamodb.constants import BINARY, DEFAULT_ENCODING
from pynamodb.exceptions import UpdateError
from pynamodb.models import Model

from ..machine import future as fut
from ..machine.state import State
from ..machine.arec import ActivationRecord

LOG = logging.getLogger(__name__)


# Make it harder to accidentally use real AWS resources:
if "DYNAMODB_ENDPOINT" not in os.environ and "USE_LIVE_AWS" not in os.environ:
    raise RuntimeError("One of DYNAMODB_ENDPOINT or USE_LIVE_AWS must be set!")

BASE_SESSION_ID = "base"


class FutureAttribute(MapAttribute):
    resolved = BooleanAttribute(default=False)
    continuations = ListAttribute(default=list)
    chain = NumberAttribute(null=True)
    value = JSONAttribute(null=True)

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return fut.Future.deserialise(super().deserialize(value).as_dict())


class StateAttribute(JSONAttribute):
    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return State.deserialise(super().deserialize(value))


class ARecAttribute(MapAttribute):
    ref_count = NumberAttribute()
    function = ListAttribute(null=True)
    dynamic_chain = NumberAttribute(null=True)
    vmid = NumberAttribute(null=True)
    call_site = NumberAttribute(null=True)
    bindings = MapAttribute(default=dict)

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return ActivationRecord.deserialise(super().deserialize(value).as_dict())


class ProbeEvent(MapAttribute):
    thread = NumberAttribute()
    time = NumberAttribute()
    event = UnicodeAttribute()
    data = MapAttribute(null=True)


class ProbeLog(MapAttribute):
    thread = NumberAttribute()
    time = NumberAttribute()
    log = UnicodeAttribute()


class Stdout(MapAttribute):
    thread = NumberAttribute()
    time = NumberAttribute()
    log = UnicodeAttribute()


class MetaAttribute(MapAttribute):
    num_threads = NumberAttribute(default=0)
    num_arecs = NumberAttribute(default=0)
    stopped = ListAttribute(default=list)
    exe = MapAttribute(null=True)
    result = UnicodeAttribute(null=True)


class SessionItem(Model):
    class Meta:
        table_name = os.environ.get("DYNAMODB_TABLE", "TealSessions")
        host = os.environ.get("DYNAMODB_ENDPOINT", None)
        region = os.environ.get("TL_REGION", None)

    session_id = UnicodeAttribute(hash_key=True)
    item_id = UnicodeAttribute(range_key=True)
    locked = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    expires_on = NumberAttribute()

    ##

    meta = MetaAttribute(null=True)
    stdout = ListAttribute(of=Stdout, null=True)
    plogs = ListAttribute(of=ProbeLog, null=True)
    pevents = ListAttribute(of=ProbeEvent, null=True)
    arec = ARecAttribute(null=True)
    future = FutureAttribute(null=True)
    state = StateAttribute(null=True)


###


def init_base_session():
    LOG.info("DB %s (%s)", SessionItem.Meta.host, SessionItem.Meta.region)
    LOG.info("DB table %s", SessionItem.Meta.table_name)
    try:
        SessionItem.get(BASE_SESSION_ID, "meta")
    except SessionItem.DoesNotExist as exc:
        LOG.info("Creating base session")
        s = SessionItem(
            BASE_SESSION_ID,
            "meta",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_on=0,  # ie, don't expire
            meta=MetaAttribute(),
        )
        s.save()


def set_base_exe(exe):
    base_session = SessionItem.get(BASE_SESSION_ID, "meta")
    base_session.meta.exe = exe.serialise()
    base_session.save()


ITEM_TTL = os.getenv("TEAL_SESSION_TTL", None)


def new_session_item(sid, item_id, **extra):
    """Helper"""
    ttl = ITEM_TTL
    if ttl is not None:
        expiry = int(int(ttl) + time.time())
    else:
        expiry = 0  # ie, don't expire if no TEAL_SESSION_TTL specified

    return SessionItem(
        session_id=sid,
        item_id=item_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        expires_on=expiry,
        **extra,
    )


def new_session() -> SessionItem:
    base_session = SessionItem.get(BASE_SESSION_ID, "meta")
    sid = str(uuid.uuid4())

    s = new_session_item(
        sid, "meta", meta=MetaAttribute(exe=base_session.meta.exe, stopped=[]),
    )
    s.save()
    new_session_item(sid, "plogs", plogs=[]).save()
    new_session_item(sid, "pevents", pevents=[]).save()
    return s


###


def try_lock(session, thread_lock) -> bool:
    """Try to acquire a lock on session, returning True if successful"""
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


class LockTimeout(Exception):
    """Timeout trying to lock session"""


class SessionLocker(AbstractContextManager):
    """Lock the session for modification (re-entrant for chain_resolve)

    https://docs.python.org/3/library/contextlib.html#reentrant-context-managers

    __enter__: Refresh session, lock it
    ...
    __exit__: release the lock and save the session

    """

    def __init__(self, session, timeout=2.0):
        self.session = session
        self.timeout = timeout
        self._thread_lock = threading.Lock()
        self.count = {}

    def __enter__(self):
        tid = threading.get_native_id()

        # re-lock if this thread has already got one lock
        if self._thread_lock.locked() and self.count.get(tid, 0) > 0:
            t = time.time() % 1000.0
            self.count[tid] += 1
            return

        start = time.time()
        while not try_lock(self.session, self._thread_lock):
            time.sleep(0.01)
            if time.time() - start > self.timeout:
                t = time.time() % 1000.0
                LOG.debug(f"{t:.3f} :: Timeout getting lock")
                raise LockTimeout

        self.count[tid] = 1

        t = time.time() % 1000.0
        LOG.debug(f"{t:.3f} :: Thread {tid} Locked")

    def __exit__(self, *exc):
        t = time.time() % 1000.0
        tid = threading.get_native_id()

        if self._thread_lock.locked() and self.count.get(tid, 0) > 1:
            self.count[tid] -= 1
            return

        self.count[tid] -= 1
        assert self.count[tid] == 0

        LOG.debug(f"{t:.3f} :: Releasing %s", self.session)
        self.session.update(
            [SessionItem.locked.set(False)], condition=(SessionItem.locked == True)
        )
        self._thread_lock.release()

        t = time.time() % 1000.0
        LOG.debug(f"{t:.3f} :: Thread {tid} Released")
