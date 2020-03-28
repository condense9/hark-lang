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

    # def probe_log(self, probe_id: int, message):


class AwsFuture(Future):
    def __init__(self, controller):
        super().__init__(controller)
        self._value = None
        self._resolved = False

    @property
    def lock(self):
        return self.controller.db.with_lock_future(self)

    @property
    def chain(self) -> AwsFuture:
        return self.controller.db.get_future_chain(self)

    @chain.setter
    def chain(self, future: AwsFuture):
        self.controller.db.set_future_chain(self, future)

    @property
    def resolved(self) -> bool:
        self._resolved, self._value = self.controller.db.get_future_state(self)
        return self._resolved

    @property
    def value(self):
        # Assume this is only called if resolved is True, after which, the value
        # never changes, so no need to get_future_state again here
        return self._value

    def set_value(self, value):
        self._value = value
        self.controller.db.resolve_future(self, value)

    @property
    def continuations(self) -> List[Tuple[MRef, int]]:
        # todo massage into proper format?
        return self.controller.db.get_future_continuations(self)

    def add_continuation(self, m: MRef, offset: int):
        self.controller.db.add_future_continuation(self, m, offset)


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
    future_type = LocalFuture

    def __init__(self, executable, db: DB, do_probe=False):
        super().__init__()
        self.db = db
        self.top_level = self.db.get_top_level_machine()
        self.finished = False
        self.result = None

    def finish(self, result):
        self.db.finish(result)
        self.finished = True
        self.result = result

    # C9Machine should have to carry around its own ID. The controller should
    # deal with that. It should pass itself to the controller, as-is.
    def stop(self, m: C9Machine):
        self.db.set_state(self.refs[m], m.state)

    def is_top_level(self, m: MRef):
        return m == self.top_level

    def new_machine(self, args: list, top_level=False) -> MRef:
        m, f = self.db.new_machine(args, top_level)
        probe = maybe_create(AwsProbe, self.do_probe)
        self.db.set_probe(m, probe)
        if top_level:
            self.top_level = m
        return m

    def probe_log(self, m: MRef, msg: str):
        self.db.probe_log(m, msg)

    def get_future(self, m: MRef) -> AwsFuture:
        return self.db.get_future(m)

    def get_state(self, m: MRef) -> State:
        return self.db.get_state(m)

    def get_probe(self, m: MRef) -> AwsProbe:
        return self.db.get_probe(m)

    def run_forked_machine(self, m: MRef, new_ip: int):
        self.db.update_machine_ip(m, new_ip)
        self._run_machine(m)

    def run_waiting_machine(self, m: MRef, offset: int, value):
        self.db.restart_machine(m, offset, value)
        self._run_machine(m)

    def run_top_level(self, args: list) -> MRef:
        m = self.new_machine(args, top_level=True)
        self.probe_log(m, f"Top Level {m}")
        self._run_machine(m)
        # TODO??

    def _run_machine(self):
        pass
        # TODO

    @property
    def machines(self):
        pass  # todo

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]


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
