"""DB interaction layer for AWS"""

import base64
import os
import pickle
import time
import uuid
import logging
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
from pynamodb.exceptions import PutError
from pynamodb.models import Model

from ..state import State


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
    resolved = BooleanAttribute(default=False)
    chain = NumberAttribute(null=True)
    value = PickleAttribute(null=True)
    continuations = ListAttribute(of=ContinuationMap, default=list)


class MachineMap(MapAttribute):
    machine_id = NumberAttribute()
    future_fk = NumberAttribute()  # FK -> FutureAttribue
    is_top_level = BooleanAttribute()
    state = PickleAttribute()
    probe_logs = ListAttribute(default=list)


class Session(Model):
    """
    A handler session
    """

    class Meta:
        table_name = "C9Sessions"
        region = "eu-west-2"
        # Localstack for testing
        host = None if "C9_IN_AWS" in os.environ else "http://localhost:4569"

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


def new_session() -> Session:
    sid = str(uuid.uuid4())
    s = Session(sid, created_at=datetime.now(), updated_at=datetime.now())
    s.save()
    return s


def new_future(session) -> FutureMap:
    f = FutureMap(future_id=session.num_futures, resolved=False)
    session.futures.append(f)
    session.num_futures += 1
    return f


def new_machine(session, args, top_level=False) -> MachineMap:
    state = State(args)
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
    # return next(f for f in session.futures if f.future_id == future_id)
    return session.futures[future_id]


def try_lock(session) -> bool:
    """Try to acquire a lock on session, returning True if successful"""
    session.refresh()
    if session.locked:
        return False

    try:
        session.update([Session.locked.set(True)], condition=(Session.locked == False))
        return True

    except PutError as e:
        if isinstance(e.cause, ClientError):
            code = e.cause.response["Error"].get("Code")
            if code == "ConditionalCheckFailedException":
                return False
        raise


class LockTimeout(Exception):
    """Timeout trying to lock session"""


class SessionLocker(AbstractContextManager):
    """Lock the session for modification (reusable)

    __enter__: Refresh session, lock it
    ...
    __exit__: save it, release the lock

    """

    def __init__(self, session, timeout=2):
        self.session = session
        self.timeout = timeout

    def __enter__(self):
        start = time.time()
        while not try_lock(self.session):
            time.sleep(0.1)
            if time.time() - start > self.timeout:
                logging.warning("Timeout getting lock")
                raise LockTimeout

    def __exit__(self, *exc):
        self.session.locked = False
        self.session.save()
