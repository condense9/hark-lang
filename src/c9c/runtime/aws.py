"""AWS (lambda / ECS) runtime

In AWS, there will be one Machine executing in the current context, and others
executing elsewhere, as part of the same "session". There is one Controller per
session.

There's a queue of "runnable machines".

Run machine: push the new machine onto the queue.
- At a fork
- When a future resolves

Stop: pop something from the queue and Start it

Start top level: make a new machine and run it
Start existing (fork or cont): take an existing stopped machine and run it


A session is created when a handler is first called. Multiple machines
(threads) may exist in the session.

Data per session:
- futures (resolved, value, chain, continuations - machine, offset)
- machines (probe logs, state - ip, stopped flag, stacks, and bindings)

We could lock it to a single object:
- session (controller info, futures, machines)

Data exchange points:
- machine forks (State of new machine set to point at the fork IP)
- machine waits on future (continuation added to that future)
- machine checks whether future is resolved
- future resolves (must refresh list of continuations)
- top level machine finishes (Controller sets session result)
- machine stops (upload the State)
- machine continues (download the State)

"""

import json
import uuid
from functools import wraps
from typing import List, Tuple

import boto3

from .. import compiler
from ..machine import Controller, Future, Probe
from ..state import State

# from .aws_db import


class MRef(int):
    pass


class AwsProbe(Probe):
    # def __init__(self, controller)
    pass


class DB:
    # PK: session_id
    # SK: item_id
    def __init__(self, session_id: str, table="c9data", region="eu-west-2"):
        self.sid = session_id
        dynamodb = boto3.resource("dynamodb", region=region)
        self._table = dynamodb.Table(table_name)

    def _get_item(self, item_id):
        result = self.table.get_item(Key={"id": event["pathParameters"]["id"]})
        return result["Item"]

    def _put_item(self, attributes):
        timestamp = str(time.time())
        item = {
            "session_id": self.sid,
            "item_id": str(uuid.uuid1()),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }.update(attributes)
        self.table.put_item(Item=item)
        return item

    def _update_ip(self, item_id: str, new_ip):
        timestamp = str(time.time())
        result = self.table.update_item(
            Key={"session_id": self.sid, "item_id": item_id},
            ExpressionAttributeNames={"#ip": "ip"},
            ExpressionAttributeValues={":ip": new_ip, ":updatedAt": timestamp},
            UpdateExpression="SET #ip=:ip, updatedAt=:updatedAt",
            ReturnValues="ALL_NEW",
        )
        return result["Attributes"]

    def _update_ds_value(self, item_id: str, offset, value):
        timestamp = str(time.time())
        result = self.table.update_item(
            Key={"session_id": self.sid, "item_id": item_id,},
            # TODO
            # ExpressionAttributeNames={"#ip": "ip"},
            # ExpressionAttributeValues={":ip": new_ip, ":updatedAt": timestamp,},
            # UpdateExpression="SET #ip=:ip, updatedAt=:updatedAt",
            ReturnValues="ALL_NEW",
        )
        return result["Attributes"]

    def new_machine(self, args: list, top_level=False) -> Tuple[MRef, AwsFuture]:
        pass  # TODO

    def finish(self, result):
        pass  # TODO

    def update_machine_ip(self, m: MRef, new_ip: int):
        # TODO assert it is stopped
        pass

    def restart_machine(self, m: MRef, offset: int, value):
        # TODO assert it is stopped
        pass

    def set_state(self, m: MRef, state: State):
        blob = pickle.dumps(state)
        # TODO

    def get_state(self, m: MRef) -> State:
        # TODO
        return pickle.loads(blob)

    ## FUTURES

    # def with_lock_future(self, f: AwsFuture):
    # def get_future_chain(self, f: AwsFuture) -> AwsFuture:
    # def set_future_chain(self, a: AwsFuture, b: AwsFuture):
    # def get_future_state(self, f: AwsFuture) -> Tuple[bool, Any]:
    # def resolve_future(self, f: AwsFuture, value):
    # def add_future_continuation(self, f: AwsFuture, m: MRef, offset: int):
    # def get_future_continuations(self, f: AwsFuture) -> List[Tuple[MRef, int]]:
    # def get_future(self, m: MRef) -> AwsFuture:

    ## PROBES


# Ugh. Need to have futures separately so that chaining is simpler. So put them
# in a separate table with their own IDs.


class AwsFutureOld(Future):
    def __init__(self, controller, db_item: db.FutureMap):
        super().__init__(controller)
        self.db_item = db_item

    @property
    def lock(self):
        # TODO make this a contextmgr
        yield self.controller.get_db_lock()
        self.controller.save_session()

    @property
    def chain(self) -> AwsFuture:
        return self.db_item.chain

    @chain.setter
    def chain(self, future: AwsFuture):
        self.db_item.chain = future.db_item.future_id

    @property
    def resolved(self) -> bool:
        self.controller.refresh_session()
        return self.db_item.resolved

    @property
    def value(self):
        # Assume this is only called if resolved is True, after which, the value
        # never changes, so no need to get_future_state again here
        return self.db_item.value

    def set_value(self, value):
        self.db_item.resolved = True
        self.db_item.value = value

    def add_continuation(self, m: C9Machine, offset: int):
        m = self.controller.this_machine_db_item
        self.db_item.continuations.append(m.machine_id, offset)

    # Probably not needed:
    def to_dict(self):
        return dict(
            resolved=self.resolved,
            chain=self.chain,
            continuations=self.continuations,
            value=self.value,
        )

    @classmethod
    def from_dict(cls, d: dict):
        f = cls()
        f.resolved = d["resolved"]
        f.chain = d["chain"]
        f.continuations = d["continuations"]
        f.value = d["value"]
        return f

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()


class AwsFuture(ChainedFuture):
    def __init__(self, data: FutureMap, lock):
        self.lock = lock
        self._data = data

    @property
    def resolved(self) -> bool:
        return self._data.resolved

    @resolved.setter
    def resolved(self, value):
        self._data.resolved = value

    @property
    def value(self):
        return self._data.value

    @value.setter
    def value(self, value):
        self._data.value = value

    @property
    def chain(self) -> AwsFuture:
        # Shared, global lock
        return AwsFuture(self._data.chain, self.lock)

    @chain.setter
    def chain(self, other: AwsFuture):
        self._data.chain = other._data.future_id

    @property
    def continuations(self):
        return self._data.continuations


# NOTE - some handlers cannot terminate early, because they have to maintain a
# connection to a client. This is a "hardware" restriction. So if an HTTP
# handler calls something async, it has to wait for it. Anything /that/ function
# calls can be properly async. But the top level has to stay alive. That isn't
# true of all kinds of Handlers!!
#
# ONLY THE ONES THAT HAVE TO SEND A RESULT BACK
#
# So actually that gets abstracted into some kind of controller interface - the
# top level "run" function. For HTTP handlers, it has to block until the
# Controller finishes. For others, it can just return. No Controller logic
# changes necessary. Just the entrypoint / wrapper.


class AwsController(Controller):
    def __init__(self, executable, session, do_probe=False):
        super().__init__()
        self.executable = executable
        self._session = session
        self.do_probe = do_probe
        self.this_is_top_level = False

    @property
    def result(self):
        return self._session.result

    @property
    def finished(self):
        return self._session.finished

    def finish(self, result):
        self._session.finished = True
        self._session.result = result
        # self._session.save()

    # @atomic_update("_session")
    def stop(self, m: C9Machine):
        assert m is self.this_machine
        self.this_machine_db_item.stopped = True
        self._session.save()

    def is_top_level(self, m: C9Machine):
        # Is the currently executing machine the top level?
        assert m is self.this_machine
        return self.this_is_top_level

    def get_state(self, m: C9Machine) -> State:
        assert m is self.this_machine
        return self.this_machine_db_item.state

    def get_probe(self, m: C9Machine) -> AwsProbe:
        assert m is self.this_machine
        return self.probe

    def probe_log(self, m: C9Machine, message: str):
        assert m is self.this_machine
        self.probe.log(message)

    def get_result_future(self, m: C9Machine) -> AwsFuture:
        # Only one C9Machine is ever running in a controller in AWS at a time,
        # so if m is a C9Machine, it must be this_machine.
        if isinstance(m, C9Machine):
            assert m is self.this_machine
            return self.this_machine_future
        else:
            assert isinstance(m, db.MachineMap)
            return AwsFuture(db.get_future(self._session, m.future_fk), self.lock)

    def is_future(self, f):
        return isinstance(f, AwsFuture)

    def get_or_wait(self, m: C9Machine, future: AwsFuture, offset: int):
        # prevent race between resolution and adding the continuation
        assert m is self.this_machine
        with self.lock:
            self._session.refresh()
            resolved = future.resolved
            if resolved:
                value = future.value
            else:
                future.continuations.append[
                    (self.this_machine_db_item.machine_id, offset)
                ]
                value = None
        return resolved, value

    def set_machine_result(self, m: C9Machine, value):
        assert m is self.this_machine
        chain_resolve(
            self.this_machine_future, value, self.run_waiting_machine,
        )

    ## After this point, only deal with MachineMap

    def new_machine(self, args: list, top_level=False) -> MachineMap:
        m = db.new_machine(self._session, args, top_level=top_level)
        self._session.save()
        return m

    def run_forked_machine(self, m: MRef, new_ip: int):
        db_m = db.get_machine(self._session, m)
        db_m.state.ip = new_ip
        self._session.save()
        self._run_machine_async(m)

    def run_waiting_machine(self, m: MRef, offset: int, value):
        db_m = db.get_machine(self._session, m)
        db_m.state.ds_set(offset, value)
        db_m.state.stopped = False
        self._session.save()
        self._run_machine_async(m)

    def run_top_level(self, args: list) -> C9Machine:
        m = self.new_machine(self._session, args, top_level=True)
        self.this_machine_probe = probe
        self.run_machine(m)
        return self.this_machine

    def run_machine(self, m: db.MachineMap):
        self.this_machine_db_item = m
        self.this_machine = C9Machine(self)
        future = db.get_future(self._session, m.future_fk)
        self.this_machine_future = AwsFuture(future, self.lock)
        self.probe = AwsProbe(m) if self.do_probe else Probe()
        self.this_is_top_level = m.is_top_level
        self.this_machine.run()


def run(executable, *args, do_probe=True):
    pass


def continue_from(executable, runtime):
    """Pick up execution from the given point"""


# For auto-gen code:
def get_entrypoint(handler):
    """Return a function that will run the given handler"""
    linked = compiler.link(compiler.compile_all(handler), entrypoint_fn=handler.label)

    @wraps(handler)
    def _f(event, context, linked=linked):
        state = LocalState([event, context])
        # FIXME
        machine.run(linked, state)
        return state.ds_pop()

    return _f
