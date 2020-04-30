"""AWS DynamoDB backed storage

In AWS, there will be one Machine executing in the current context, and others
executing elsewhere, as part of the same "session". There is one Controller per
session.

Data per session:
- futures (resolved, value, chain, continuations - machine, offset)
- machines (probe logs, state - ip, stopped flag, stacks, and bindings)

Data exchange points:
- machine forks (State of new machine set to point at the fork IP)
- machine waits on future (continuation added to that future)
- machine checks whether future is resolved
- future resolves (must refresh list of continuations)
- top level machine finishes (Controller sets session result)
- machine stops (upload the State)
- machine continues (download the State)
"""

import logging
import time
import traceback
import uuid
import warnings
from functools import singledispatchmethod, wraps
from typing import List, Tuple

import boto3

from ..machine import TlMachine, Probe
from ..machine import future as fut
from ..machine import instructionset as mi
from ..machine import types as mt
from ..machine.executable import Executable
from ..machine.instruction import Instruction
from ..machine.state import State
from . import ddb_model as db

LOG = logging.getLogger(__name__)


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
        self.evaluator_cls = Evaluator
        if session.executable:
            self.executable = Executable.deserialise(session.executable)
        self.lock = lock

    def set_executable(self, exe):
        self.executable = exe
        with self.lock:
            self.session.executable = exe.serialise()

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

    @property
    def finished(self):
        self.session.refresh()
        return self.session.finished

    @finished.setter
    def finished(self, value):
        self.session.finished = value

    @property
    def result(self):
        return self.session.result

    @result.setter
    def result(self, value):
        self.session.result = value

    def get_state(self, vmid):
        # refresh session?
        return self.session.machines[vmid].state

    def get_probe(self, vmid):
        # TODO - machine-specific probes?
        return Probe()

    def get_future(self, val):
        # TODO - clean up (see local.py)
        if isinstance(val, mt.TlFuturePtr):
            ptr = val.value
        else:
            assert type(val) is int
            ptr = val
        LOG.info("Getting future: %d (%s)", ptr, val)
        f = self.session.machines[ptr].future
        return f

    def set_future_value(self, vmid, offset, value):
        with self.lock:
            LOG.info("Resolving top of stack to %s (on machine %d)", value, vmid)
            state = self.session.machines[vmid].state
            state.stopped = False
            state.ds_set(offset, value)

    def finish(self, vmid, value) -> list:
        LOG.info("Finishing %d %s", vmid, value)
        with self.lock:
            return fut.finish(self, vmid, value)

    def get_or_wait(self, vmid, future_ptr, state, probe):
        with self.lock:
            resolved, value = fut.get_or_wait(self, vmid, future_ptr)
            if not resolved:
                state.stopped = True
                self.session.machines[vmid].state = state
                self.session.machines[vmid].probe_logs += probe.logs
            return resolved, value

    @property
    def machines(self):
        return list(self.session.machines)

    @property
    def probes(self):
        return [Probe.with_logs(m.probe_logs) for m in self.session.machines]

    @property
    def stdout(self):
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
