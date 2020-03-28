"""DB interaction layer for AWS"""

import os
import pickle
import base64

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
        return pickle.loads(base64.b64decode(value))


class StateAttribute(JSONAttribute):
    def serialize(self, value):
        return super().serialize(value.to_dict())

    def deserialize(self, value):
        return State.from_dict(super().deserialize(value))


class MachineMap(MapAttribute):
    machine_id = NumberAttribute()
    state = StateAttribute()
    logs = ListAttribute(default=[])


class FutureMap(MapAttribute):
    future_id = NumberAttribute()
    resolved = BooleanAttribute(default=False)
    value = PickleAttribute(null=True)  # Will start null
    continuations = ListAttribute(default=[])  # of ContinuationAttribute


class ContinuationAttribute(Attribute):
    machine_id = NumberAttribute()
    offset = NumberAttribute()


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
    futures = ListAttribute(of=FutureMap, default=[])
    machines = ListAttribute(of=MachineMap, default=[])


class LocalSessionModel(BaseSessionModel):
    class Meta:
        table_name = "C9Sessions"
        region = "eu-west-2"
        host = "http://localhost:4569"


if "C9_IN_AWS" in os.environ:
    Session = BaseSessionModel
else:
    Session = LocalSessionModel
