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
from ..machine import types as mt
from ..machine.executable import Executable
from ..machine import future as fut
from ..machine.instruction import Instruction
from ..machine.state import State
from . import ddb_model as db

LOG = logging.getLogger()


# TODO
#
# - Reduce the amount of data transferred. It makes it super slow
# - Profile this, to be sure
# - Probe content viewer (console/web-ui)
# - Session viewer (web-ui)
# - Provide a function restart-on-error interface (console/web-ui??)


class DataController:
    def __init__(self, session, lock):
        super().__init__()
        self.session = session
        if session.executable:
            self.executable = Executable.deserialise(session.executable)
        self.lock = lock

    def set_executable(self, exe):
        assert exe
        self.executable = exe
        with self.lock:
            self.session.executable = exe.serialise()

    def new_machine(self, args, fn_name, is_top_level=False):
        if fn_name not in self.executable.locations:
            raise Exception(f"Function `{fn_name}` doesn't exist")
        with self.lock:
            future = db.AwsFuture(self.lock)
            vmid = db.new_machine(self.session, args, future, top_level=is_top_level)
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
        # self.session.refresh()
        return self.session.finished

    @finished.setter
    def finished(self, value):
        with self.lock:
            self.session.finished = value

    @property
    def result(self):
        return self.session.result

    @result.setter
    def result(self, value):
        with self.lock:
            self.session.result = value

    def get_state(self, vmid):
        return self.session.machines[vmid].state

    def get_probe(self, vmid):
        return Probe()

    def get_future(self, vmid):
        return self.session.futures[vmid]

    def set_future_value(self, vmid, offset, value):
        with self.lock:
            LOG.info("Resolving %d to '%s' (on %d)", offset, value, vmid)
            state = self.session.machines[vmid].state
            state.stopped = False
            state.ds_set(offset, value)

    def finish(self, vmid, value) -> list:
        return fut.finish(self, vmid, value)

    def get_or_wait(self, vmid, future_ptr, offset):
        return fut.get_or_wait(self, vmid, future_ptr, offset)

    @property
    def machines(self):
        # self.session.refresh()
        return list(self.session.machines)

    @property
    def probes(self):
        # self.session.refresh()
        return [Probe.with_logs(m.probe_logs) for m in self.session.machines]

    @property
    def stdout(self):
        # self.session.refresh()
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
