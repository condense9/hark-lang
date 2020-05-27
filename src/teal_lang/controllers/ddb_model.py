"""DB interaction layer for AWS"""

import base64
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

LOG = logging.getLogger(__name__)


class FutureAttribute(MapAttribute):
    resolved = BooleanAttribute()
    continuations = ListAttribute()
    chain = NumberAttribute()
    value = JSONAttribute()

    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return fut.Future.deserialise(super().deserialize(value).as_dict())


class StateAttribute(JSONAttribute):
    def serialize(self, value):
        return super().serialize(value.serialise())

    def deserialize(self, value):
        return State.deserialise(super().deserialize(value))


class ProbeEvent(MapAttribute):
    time = NumberAttribute()
    event = UnicodeAttribute()
    data = MapAttribute(null=True)


class MachineMap(MapAttribute):
    state = StateAttribute()
    probe_logs = ListAttribute(default=list)
    probe_events = ListAttribute(of=ProbeEvent, default=list)
    future = FutureAttribute()
    exception = UnicodeAttribute(default=None)


# Make it harder to accidentally use real AWS resources:
if "DYNAMODB_ENDPOINT" not in os.environ and "USE_LIVE_AWS" not in os.environ:
    raise RuntimeError("One of DYNAMODB_ENDPOINT or USE_LIVE_AWS must be set!")


class Session(Model):
    """
    A handler session
    """

    class Meta:
        table_name = os.environ.get("DYNAMODB_TABLE", "TealSessions")
        host = os.environ.get("DYNAMODB_ENDPOINT", None)
        region = os.environ.get("TL_REGION", None)

    # Very simple, SINGLE-ENTRY, global lock for the whole session. Brutal -
    # could be optimised later
    locked = BooleanAttribute(default=False)

    # To double-check the lock logic...
    # https://pynamodb.readthedocs.io/en/latest/optimistic_locking.html
    version = VersionAttribute()

    expires_on = NumberAttribute()

    # Naming: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.NamingRules
    # Types: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
    session_id = UnicodeAttribute(hash_key=True)
    finished = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    result = JSONAttribute(null=True)
    num_machines = NumberAttribute(default=0)
    # NOTE!! Big gotcha - be careful what you pass in as default; pynamodb
    # saves a reference. So don't use a literal "[]"!
    # futures = ListAttribute(of=FutureAttribute, default=list)
    machines = ListAttribute(of=MachineMap, default=list)
    top_level_vmid = NumberAttribute(null=True)
    executable = MapAttribute(null=True)
    stdout = ListAttribute(default=list)


BASE_SESSION_ID = "base"


def init_base_session():
    LOG.info("DB %s (%s)", Session.Meta.host, Session.Meta.region)
    LOG.info("DB table %s", Session.Meta.table_name)
    try:
        Session.get(BASE_SESSION_ID)
    except Session.DoesNotExist as exc:
        LOG.info("Creating base session")
        s = Session(
            BASE_SESSION_ID,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_on=0,  # ie, don't expire
        )
        s.save()


def set_base_exe(exe):
    base_session = Session.get(BASE_SESSION_ID)
    base_session.executable = exe.serialise()
    base_session.save()


def new_session() -> Session:
    base_session = Session.get(BASE_SESSION_ID)
    sid = str(uuid.uuid4())

    ttl = os.getenv("TEAL_SESSION_TTL", None)
    if ttl:
        expiry = int(int(ttl) + time.time())
    else:
        expiry = 0  # ie, don't expire if no TEAL_SESSION_TTL specified

    s = Session(
        sid,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        expires_on=expiry,
        executable=base_session.executable,
    )
    s.save()
    return s


def new_machine(session, args, top_level=False) -> MachineMap:
    state = State(*args)
    vmid = session.num_machines
    future = fut.Future()
    session.num_machines += 1
    m = MachineMap(
        # --
        state=state,
        future=future,
    )
    if top_level:
        session.top_level_vmid = vmid
    session.machines.append(m)
    # session.futures.append(future)
    assert len(session.machines) == session.num_machines
    LOG.info("New machine: %d", vmid)
    return vmid


def try_lock(session, thread_lock) -> bool:
    """Try to acquire a lock on session, returning True if successful"""
    if not thread_lock.acquire(blocking=False):
        return False

    try:
        session.refresh()
        session.update([Session.locked.set(True)], condition=(Session.locked == False))
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

    def __enter__(self):
        t = time.time() % 1000.0
        tid = threading.get_native_id()

        start = time.time()
        while not try_lock(self.session, self._thread_lock):
            time.sleep(0.01)
            if time.time() - start > self.timeout:
                t = time.time() % 1000.0
                LOG.debug(f"{t:.3f} :: Timeout getting lock")
                raise LockTimeout

        t = time.time() % 1000.0
        LOG.info(f"{t:.3f} :: Thread {tid} Locked")

    def __exit__(self, *exc):
        t = time.time() % 1000.0

        self.session.locked = False
        LOG.debug(f"{t:.3f} :: Saving %s", self.session)
        self.session.save()
        self._thread_lock.release()

        t = time.time() % 1000.0
        tid = threading.get_native_id()
        LOG.info(f"{t:.3f} :: Thread {tid} Released")
