"""DB interaction layer for AWS"""

import base64
import logging
import os
import pickle
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

from ..constants import C9_DDB_TABLE_NAME, C9_DDB_REGION
from ..machine.state import State

logger = logging.getLogger()


# https://pynamodb.readthedocs.io/en/latest/attributes.html#list-attributes
class PickleAttribute(Attribute):
    """
    This class will serializer/deserialize any picklable Python object.
    The value will be stored as a binary attribute in DynamoDB.
    """

    attr_type = BINARY

    def serialize(self, value):
        """
        The super class takes the binary string returned from pickle.dumps
        and encodes it for storage in DynamoDB
        """
        return pickle.dumps(value, protocol=5)

    def deserialize(self, value):
        # NOTE - there's an extra level of b64 encoding happening somewhere, and
        # I'm not sure where (either DynamoDB or PynamoDB). But the value we get
        # here must be decoded first!
        # https://github.com/pynamodb/PynamoDB/blob/master/pynamodb/attributes.py#L323
        return pickle.loads(base64.b64decode(value))


class StateAttribute(JSONAttribute):
    def serialize(self, value):
        return super().serialize(value.to_dict())

    def deserialize(self, value):
        return State.from_dict(super().deserialize(value))


class ContinuationMap(MapAttribute):
    machine_id = NumberAttribute()
    offset = NumberAttribute()


class FutureMap(MapAttribute):
    future_id = NumberAttribute()
    user_id = NumberAttribute(null=True)
    resolved = BooleanAttribute(default=False)
    chain = NumberAttribute(null=True)
    value = PickleAttribute(null=True)
    continuations = ListAttribute(of=ContinuationMap, default=list)


class MachineMap(MapAttribute):
    machine_id = NumberAttribute()
    future_fk = NumberAttribute()  # FK -> FutureAttribue
    is_top_level = BooleanAttribute()
    state = PickleAttribute()  # FIXME state should be JSON-able
    probe_logs = ListAttribute(default=list)


class ExecutableMap(MapAttribute):
    locations = MapAttribute()
    foreign = MapAttribute()
    code = ListAttribute()
    # example:
    # ExecutableMap(locations={'foo': 23, 'bar': 50},
    #               foreign={'a': ['m', 'f'], 'b': ['m2', 'f2']},
    #               code=[['instr', 'arg'], ['istr2', 'arg2']])


class Session(Model):
    """
    A handler session
    """

    class Meta:
        host = os.environ.get("DYNAMODB_ENDPOINT", None)
        table_name = os.environ.get("DYNAMODB_TABLE", C9_DDB_TABLE_NAME)
        region = os.environ.get("DYNAMODB_REGION", C9_DDB_REGION)

    # Very simple, SINGLE-ENTRY, global lock for the whole session. Brutal -
    # could be optimised later
    locked = BooleanAttribute(default=False)

    # To double-check the lock logic...
    # https://pynamodb.readthedocs.io/en/latest/optimistic_locking.html
    version = VersionAttribute()

    # Naming: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.NamingRules
    # Types: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
    session_id = UnicodeAttribute(hash_key=True)
    finished = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    result = JSONAttribute(null=True)  # JSON? Really?
    num_futures = NumberAttribute(default=0)
    num_machines = NumberAttribute(default=0)
    # NOTE!! Big gotcha - be careful what you pass in as default; pynamodb
    # saves a reference. So don't use a literal "[]"!
    futures = ListAttribute(of=FutureMap, default=list)
    machines = ListAttribute(of=MachineMap, default=list)
    executable = ExecutableMap()


BASE_SESSION_ID = 0


def new_session() -> Session:
    base_session = Session.get(BASE_SESSION_ID)
    sid = str(uuid.uuid4())
    s = Session(
        sid,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        executable=base_session.executable,
    )
    s.save()
    return s


def new_future(session) -> FutureMap:
    f = FutureMap(future_id=session.num_futures, resolved=False)
    session.futures.append(f)
    session.num_futures += 1
    return f


def new_machine(session, args, top_level=False) -> MachineMap:
    state = State(*args)
    f = new_future(session)
    m = MachineMap(
        # --
        machine_id=session.num_machines,
        future_fk=f.future_id,
        state=state,
        is_top_level=top_level,
    )
    session.machines.append(m)
    session.num_machines += 1
    return m


def get_machine(session, machine_id: int):
    return session.machines[machine_id]


def get_future(session, future_id: int):
    return session.futures[future_id]


def get_user_future(session, user_future_id: int):
    return next(f for f in session.futures if f.user_future_id == user_future_id)


def try_lock(session) -> bool:
    """Try to acquire a lock on session, returning True if successful"""
    session.refresh()
    if session.locked:
        return False

    try:
        session.update([Session.locked.set(True)], condition=(Session.locked == False))
        return True

    except UpdateError as e:
        if isinstance(e.cause, ClientError):
            code = e.cause.response["Error"].get("Code")
            if code == "ConditionalCheckFailedException":
                return False
        raise


class LockTimeout(Exception):
    """Timeout trying to lock session"""


class SessionLocker(AbstractContextManager):
    """Lock the session for modification (re-entrant for chain_resolve)

    __enter__: Refresh session, lock it
    ...
    __exit__: save it, release the lock

    """

    def __init__(self, session, timeout=2):
        self.session = session
        self.timeout = timeout
        self.machine_id = None
        self.lock_count = 0

    def __enter__(self):
        logger.info(f"{self} - {self.lock_count}")
        if self.lock_count:
            self.lock_count += 1
            logger.debug(f"({self.machine_id}) :: Re-locking ({self.lock_count})")
            return

        start = time.time()
        while not try_lock(self.session):
            time.sleep(0.01)
            if time.time() - start > self.timeout:
                logger.debug(f"({self.machine_id}) :: Timeout getting lock")
                raise LockTimeout

        self.lock_count += 1
        logger.debug(f"({self.machine_id}) :: Locked ({self.lock_count})")

    def __exit__(self, *exc):
        self.lock_count -= 1
        if self.lock_count == 0:
            self.session.locked = False
            self.session.save()
        logger.debug(f"({self.machine_id}) :: Released ({self.lock_count})")
