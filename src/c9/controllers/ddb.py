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
"""

import logging
import time
import traceback
import uuid
import warnings
from functools import singledispatchmethod, wraps
from typing import List, Tuple

import boto3

from ..machine import C9Machine, Probe
from ..machine import instructionset as mi
from ..machine.executable import Executable
from ..machine.future import ChainedFuture
from ..machine.instruction import Instruction
from ..machine.state import State
from . import ddb_model as db
from .ddb_model import ContinuationMap, FutureMap, MachineMap

LOG = logging.getLogger()


# TODO
#
# - Reduce the amount of data transferred. It makes it super slow
# - Profile this, to be sure
# - Probe content viewer (console/web-ui)
# - Session viewer (web-ui)
# - Provide a function restart-on-error interface (console/web-ui??)
#
# Can you build custom picklers for objects? Probably. Pickling the whole state
# object is so ugly.


class AwsFuture(ChainedFuture):
    def __init__(self, session, future_id, lock):
        # ALL access to this future must be wrapped in a db lock/update, as we
        # access _data directly here. The user is responsible for this.
        #
        # NOTE - lock member is required by chain_resolve. Icky.
        self.lock = lock
        self.session = session
        self.future_id = future_id

    def __repr__(self):
        return f"<Future[{self.future_id}] {self.resolved} {self.value}>"

    @property
    def _data(self):
        # We can't assign data once at __init__ because the underlying pointer
        # changes
        return self.session.futures[self.future_id]

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
    def chain(self) -> ChainedFuture:
        # All futures share the same lock (could optimise later)
        if self._data.chain:
            return AwsFuture(self.session, self._data.chain, self.lock)

    @chain.setter
    def chain(self, other: ChainedFuture):
        self._data.chain = other.future_id

    @property
    def continuations(self):
        return [(c.machine_id, c.offset) for c in self._data.continuations]

    def add_continuation(self, machine_id, offset):
        c = ContinuationMap(machine_id=machine_id, offset=offset)
        self._data.continuations.append(c)


def load_exe(session) -> Executable:
    smap = session.executable
    return Executable(locations=smap.locations, foreign=smap.foreign, code=smap.code)


class DataController:
    def __init__(self, session):
        super().__init__()
        self.executable = None
        self.session = session
        self.lock = db.SessionLocker(session)

    def set_executable(self, exe):
        self.executable = exe

    def new_machine(self, args, fn_name, is_top_level=False):
        if fn_name not in self.executable.locations:
            raise Exception(f"Function `{fn_name}` doesn't exist")
        with self.lock:
            vmid = db.new_machine(self.session, args, top_level=is_top_level)
            state = self.session.machines[vmid].state
            state.ip = self.executable.locations[fn_name]
        return vmid

    def is_top_level(self, vmid):
        return vmid == self.session.top_level_vmid

    def stop(self, vmid, state, probe):
        with self.lock:
            assert state.stopped
            LOG.info(f"Machine stopped {vmid}")
            self.session.machines[vmid].state = state
            self.session.machines[vmid].probe_logs += probe.logs

    def finish(self, vmid, result):
        with self.lock:
            if self.is_top_level(vmid):
                LOG.info(f"Top Level Finished - {result}")
                self.session.finished = True
                self.session.result = result

    @property
    def finished(self):
        self.session.refresh()
        return self.session.finished

    @property
    def result(self):
        return self.session.result

    def get_result_future(self, vmid) -> AwsFuture:
        m = self.session.machines[vmid]
        return AwsFuture(self.session, m.future_fk, self.lock)

    def get_state(self, vmid):
        with self.lock:
            return self.session.machines[vmid].state

    def get_probe(self, vmid):
        return Probe()

    def set_future_value(self, vmid, offset, value):
        with self.lock:
            LOG.info("Resolving %d to '%s' (on %d)", offset, value, vmid)
            state = self.session.machines[vmid].state
            state.stopped = False
            state.ds_set(offset, value)

    def get_or_wait(self, vmid, future: AwsFuture, offset: int):
        # prevent race between resolution and adding the continuation
        with self.lock:
            # Refresh it:
            future = AwsFuture(self.session, future.future_id, self.lock)
            resolved = future.resolved
            if resolved:
                value = future.value
            else:
                future.add_continuation(vmid, offset)
                value = None
        return resolved, value

    def is_future(self, f):
        return isinstance(f, AwsFuture)

    @property
    def machines(self):
        self.session.refresh()
        return list(self.session.machines)

    @property
    def probes(self):
        self.session.refresh()
        return [Probe.with_logs(m.probe_logs) for m in self.session.machines]

    @property
    def stdout(self):
        self.session.refresh()
        return [m.stdout for m in self.session.machines]


class Evaluator:
    def __init__(self, parent):
        self.vmid = parent.vmid
        self.state = parent.state
        self.data_controller = parent.data_controller

    @singledispatchmethod
    def evali(self, i: Instruction):
        """Evaluate instruction"""
        assert isinstance(i, Instruction)
        raise NotImplementedError(i)

    @evali.register
    def _(self, i: mi.Print):
        # Leave the value in the stack - print returns itself
        val = self.state.ds_peek(0)
        t = time.time()
        line = f"{t:5.5f} | {val}"
        with self.data_controller.lock:
            self.data_controller.session.machines[self.vmid].stdout.append(line)

    @evali.register
    def _(self, i: mi.Future):
        raise NotImplementedError
