"""DB interaction layer for AWS"""

import base64
import os
import pickle
import uuid
from datetime import datetime

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
)
from pynamodb.constants import BINARY, DEFAULT_ENCODING
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


class ContinuationAttribute(Attribute):
    machine_id = NumberAttribute()
    offset = NumberAttribute()


class FutureMap(MapAttribute):
    future_id = NumberAttribute()
    resolved = BooleanAttribute(default=False)
    chain = NumberAttribute(null=True)
    value = PickleAttribute(null=True)
    continuations = ListAttribute(default=list)  # of ContinuationAttribute


class MachineMap(MapAttribute):
    machine_id = NumberAttribute()
    future_fk = NumberAttribute()  # FK -> FutureAttribue
    is_top_level = BooleanAttribute()
    # state = StateAttribute()
    state = PickleAttribute()
    probe_logs = ListAttribute(default=list)


class BaseSessionModel(Model):
    """
    A handler session
    """

    class Meta:
        table_name = "C9Sessions"
        region = "eu-west-2"

    # Naming: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.NamingRules
    # Types: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.NamingRulesDataTypes.html#HowItWorks.DataTypes
    session_id = UnicodeAttribute(hash_key=True)
    finished = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    # TODO https://pynamodb.readthedocs.io/en/latest/optimistic_locking.html?highlight=increment
    locked = BooleanAttribute(default=False)  # Whole session lock - brutal
    result = JSONAttribute(null=True)  # JSON? Really?
    num_futures = NumberAttribute(default=0)
    num_machines = NumberAttribute(default=0)
    # NOTE!! Big gotcha - be careful what you pass in as default; pynamodb
    # saves a reference. So don't use a literal "[]"!
    futures = ListAttribute(of=FutureMap, default=list)
    machines = ListAttribute(of=MachineMap, default=list)


class LocalSessionModel(BaseSessionModel):
    class Meta:
        table_name = "C9Sessions"
        region = "eu-west-2"
        host = "http://localhost:4569"


if "C9_IN_AWS" in os.environ:
    Session = BaseSessionModel
else:
    Session = LocalSessionModel


def new_session() -> Session:
    sid = str(uuid.uuid4())
    return Session(sid, created_at=datetime.now(), updated_at=datetime.now())


def new_future(session) -> FutureMap:
    f = FutureMap(future_id=session.num_futures, resolved=False)
    session.futures.append(f)
    session.num_futures += 1
    return f


def new_machine(session, args, is_top_level=False) -> MachineMap:
    state = State(args)
    f = new_future(session)
    m = MachineMap(
        # --
        machine_id=session.num_machines,
        future_fk=f.future_id,
        state=state,
        is_top_level=is_top_level,
    )
    session.machines.append(m)
    session.num_machines += 1
    return m


def get_machine(session, machine_id):
    return session.machines[machine_id]


def get_future(session, future_id):
    # return next(f for f in session.futures if f.future_id == future_id)
    return session.futures[future_id]


# @contextmgr
# def lock_and_save(session):
