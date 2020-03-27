"""AWS (lambda / ECS) runtime

In AWS, there will be one Machine executing in the current context, and
others executing elsewhere.

There's a queue of "runnable machines".

Run machine: push the new machine onto the queue.
- At a fork
- When a future resolves

Stop: pop something from the queue and Start it

Start top level: make a new machine and run it
Start existing (fork or cont): take an existing stopped machine and run it

"""

from typing import List, Tuple
from functools import wraps

from .. import compiler
from ..machine import Future, Probe, State, Controller


class AwsProbe(Probe):
    pass


class MRef(int):
    pass


class AwsFuture(Future):
    def __init__(self, storage):
        super().__init__()
        # self._chain
        # self._continuations
        # self._value
        # self._resolved

    @property
    def lock(self):
        raise NotImplementedError

    @property
    def chain(self) -> AwsFuture:
        raise NotImplementedError

    @chain.setter
    def chain(self, future: AwsFuture):
        raise NotImplementedError

    @property
    def value(self):
        raise NotImplementedError

    @value.setter
    def value(self, val):
        raise NotImplementedError

    @property
    def resolved(self) -> bool:
        raise NotImplementedError

    @resolved.setter
    def resolved(self, value: bool):
        raise NotImplementedError

    @property
    def continuations(self) -> List[Tuple[MRef, int]]:
        raise NotImplementedError

    def add_continuation(self, m: MRef, offset: int):
        pass  # todo


# TODO - what do I actually need to do with the DB?
# class DB:
# ...
#
# A session is created when a handler is first called. Multiple machines
# (threads) may exist in the session.
#
# Data per session:
# - machine state (State)
# - probe data
# - futures (id, resolved, value, chain, continuations)
#
# Data exchange points:
# - machine forks (State of new machine set to point at the fork IP)
# - machine waits on future (continuation added to that future)
# - future resolves (must refresh list of continuations)
# - top level machine finishes (Controller sets session result)
# - machine stops (upload the State)
# - machine continues (download the State)


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

    def __init__(self, executable, do_probe=False):
        super().__init__()
        self.top_level  # todo

    def finish(self, result):
        pass  # todo

    def stop(self, m: MRef):
        pass  # todo Could do something like sync the machine's state

    def is_top_level(self, m: MRef):
        return m == self.top_level

    def new_machine(self, args: list, top_level=False) -> MRef:
        pass  # todo

    def probe_log(self, m: MRef, msg: str):
        pass  # todo

    def get_future(self, m: MRef) -> AwsFuture:
        pass  # todo

    def get_state(self, m: MRef) -> State:
        pass  # todo

    def get_probe(self, m: MRef) -> AwsProbe:
        return AwsProbe(self.session_id,)

    def run_forked_machine(self, m: MRef, new_ip: int):
        pass  # todo

    def run_waiting_machine(self, m: MRef, offset: int, value):
        pass  # todo

    def run_top_level(self, args: list) -> MRef:
        pass  # todo

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
