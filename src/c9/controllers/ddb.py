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
from functools import wraps
from typing import List, Tuple

import boto3

from ..machine import C9Machine, ChainedFuture, Controller, Probe, chain_resolve
from ..machine.state import State
from ..machine.executable import Executable
from . import ddb_model as db
from .ddb_model import ContinuationMap, FutureMap, MachineMap

logger = logging.getLogger()


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


class AwsProbe(Probe):
    def __init__(self, m: MachineMap):
        self.m = m
        self._logs = list(m.probe_logs)  # Retrieve existing logs
        self._step = 0

    def log(self, msg):
        self._logs.append(f"*** <{self.m.machine_id}> {msg}")

    def on_step(self, m: C9Machine):
        self._step += 1
        self.log(f"[step={self._step}, ip={m.state.ip}] {m.instruction}")
        self._logs.append("Data: " + str(tuple(m.state._ds)))

    def on_stopped(self, m: C9Machine):
        self._step += 1
        self.log(f"[step={self._step}] :: stopped")

    @property
    def logs(self):
        return list(self._logs)


class AwsFuture(ChainedFuture):
    def __init__(self, session, future_id, lock):
        # ALL access to this future must be wrapped in a db lock/update, as we
        # access _data directly here. The user is responsible for this.
        #
        # NOTE - lock member is required by chain_resolve. Icky.
        self.lock = lock
        self._session = session
        self.future_id = future_id

    def __repr__(self):
        return f"<Future[{self.future_id}] {self.resolved} {self.value}>"

    @property
    def _data(self):
        # We can't assign data once at __init__ because the underlying pointer
        # changes
        return db.get_future(self._session, self.future_id)

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
            return AwsFuture(self._session, self._data.chain, self.lock)

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


class Controller(Controller):
    def __init__(self, executor, session):
        super().__init__()
        self.executable = load_exe(session)
        self._session = session
        self.lock = db.SessionLocker(session)
        self.this_is_top_level = False
        self.this_probe = None
        self.executor = executor

    def finish(self, result):
        logger.info(f"Top Level Finished - {result}")
        with self.lock:
            self._session.finished = True
            self._session.result = result

    @property
    def finished(self):
        self._session.refresh()
        return self._session.finished

    @property
    def result(self):
        return self._session.result

    def stop(self, m: C9Machine):
        assert m is self.this_machine
        self.probe_log("Stopping, uploading state and probe logs")
        with self.lock:
            m_id = self.this_id
            self._session.machines[m_id].state = self.this_state
            self._session.machines[m_id].probe_logs = self.this_probe.logs

    def is_top_level(self, m: C9Machine):
        # Is the currently executing machine the top level?
        assert m is self.this_machine
        return self.this_is_top_level

    def probe_log(self, message: str):
        self.this_probe.log(f"[CTRL] {message}")

    def get_result_future(self, m: C9Machine) -> AwsFuture:
        # Only one C9Machine is ever running in a controller in AWS at a time,
        # so if m is a C9Machine, it must be this_machine.
        # self._session.
        if isinstance(m, C9Machine):
            assert m is self.this_machine
            return self.this_future
        else:
            assert isinstance(m, MachineMap)
            return AwsFuture(self._session, m.future_fk, self.lock)

    def is_future(self, f):
        return isinstance(f, AwsFuture)

    def get_or_wait(self, m: C9Machine, future: AwsFuture, offset: int):
        assert m is self.this_machine
        # prevent race between resolution and adding the continuation
        with self.lock:
            # Refresh it:
            future = AwsFuture(self._session, future.future_id, self.lock)
            resolved = future.resolved
            if resolved:
                value = future.value
            else:
                future.add_continuation(self.this_id, offset)
                value = None
        return resolved, value

    # No need to lock - chain_resolve will do it
    def set_machine_result(self, m: C9Machine, value):
        assert m is self.this_machine
        future = self.this_future
        resolved = chain_resolve(future, value, self.run_waiting_machine)
        self.probe_log(
            f"Resolved {future}" if resolved else f"Chained {future} to {value}"
        )

    ## After this point, only deal with MachineMap

    def new_machine(self, args: list) -> MachineMap:
        with self.lock:
            m = db.new_machine(self._session, args, top_level=False)
        return m

    def run_forked_machine(self, m: MachineMap, new_ip: int):
        assert isinstance(m, MachineMap)
        # TODO - different launchers depending on function!
        with self.lock:
            self._session.machines[m.machine_id].state.ip = new_ip
        self.run_machine_async(m.machine_id)

    def run_waiting_machine(self, machine_id: int, offset: int, value):
        # This is called from chain_resolve. See self.get_or_wait - the
        # continuation holds machine_id
        with self.lock:
            machine = self._session.machines[machine_id]
            probe = AwsProbe(machine)
            probe.log(f"Continuing, {offset} -> {value}")
            machine.state.ds_set(offset, value)
            machine.state.stopped = False
        self.run_machine_async(machine_id)

    def run_machine_async(self, machine_id: int):
        assert isinstance(machine_id, int)
        self.this_probe.log(f"Starting new machine asynchronously - {machine_id}")
        self.executor.run(self._session.session_id, machine_id)

    def run_machine(self, machine_id: int):
        m = db.get_machine(self._session, machine_id)
        self.lock.machine_id = m.machine_id
        self.this_id = machine_id
        self.this_state = m.state
        self.this_probe = AwsProbe(m)
        self.this_future = AwsFuture(self._session, m.future_fk, self.lock)
        self.this_is_top_level = m.is_top_level
        self.this_machine = C9Machine(self, self.this_state, self.this_probe)
        self.probe_log(f"Running machine - {m.machine_id} ({m.is_top_level})")
        self.this_machine.run()

    @property
    def probes(self):
        self._session.refresh()
        return [AwsProbe(m) for m in self._session.machines]

    @property
    def machine_data(self):
        # Avoiding refreshing to reduce data transfer...
        return list(self._session.machines)

    @singledispatchmethod
    def evali(self, i: Instruction, m):
        """Evaluate instruction"""
        assert isinstance(i, Instruction)
        raise NotImplementedError

    @evali.register
    def _(self, i: mi.Print, m):
        raise NotImplementedError

    @evali.register
    def _(self, i: mi.Future, m):
        val = state.ds_pop(0)
        with self.lock:
            future = new_future(session)
            # The "user_id" allows external retrieval of the correct future. TODO
            # ensure uniqueness in the DB?
            future.user_id = val
            state.ds_push(AwsFuture(self._session, future.future_id, self.lock))


class Interface:
    def __init__(self, controller):
        self.controller = controller
        self.defs = {}
        self.foreign = {}

    # User interface
    def _build_exe(self):
        location = 0
        code = []
        locations = {}
        for fn_name, fn_code in self.defs.items():
            locations[fn_name] = location
            code += fn_code
            location += len(fn_code)
        return Executable(locations, self.foreign, code)

    def add_def(self, name, code):
        # If any machines are running, they will break!
        LOG.info("Defining `%s` (%d instructions)", name, len(code))
        self.defs[name] = code

    def importpy(self, dest_name, mod_name, fn_name):
        LOG.info("Importing `%s` from %s", fn_name, mod_name)
        self.foreign[dest_name] = load_function_from_module(fn_name, mod_name)

    def callf(self, name, args):
        exe = self._build_exe()

        self.controller.executable = exe

        if name not in exe.locations:
            raise Exception(f"Function `{name}` doesn't exist")
        LOG.info("Calling `%s`", name)
        m = self.controller.new_machine(args, top_level=True)
        state = self.controller.get_state(m)
        state.ip = exe.locations[name]
        LOG.info("Jumping to %d", state.ip)
        self.controller.run_machine(m)

    def resume(self, name, code):
        # not relevant locally?
        raise NotImplementedError

    def wait_for_finish(self, sleep_interval=0.01):
        try:
            while not self.controller.finished:
                time.sleep(sleep_interval)

                for probe in self.controller.probes:
                    if isinstance(probe, LocalProbe) and probe.early_stop:
                        raise Exception(
                            f"{m} forcibly stopped by probe (too many steps)"
                        )

                if self.controller.exception:
                    raise ThreadDied from self.controller.exception.exc_value

            if not all(
                self.controller.get_state(m).stopped for m in self.controller.machines
            ):
                raise Exception("Terminated, but not all machines stopped!")

        # except ThreadDied:
        #     raise

        except Exception as e:
            warnings.warn("Unexpected Exception!! Returning controller for analysis")
            traceback.print_exc()


## Entrypoints


def run_existing(executor, executable, session_id, machine_id):
    """Run an existing session and machine"""
    session = db.Session.get(session_id)
    controller = Controller(executor, executable, session)
    controller.run_machine(machine_id)
    return controller


def resolve_and_run(executor, executable, session_id, user_future_id, value):
    """Manually resolve a future in a session

    USER_FUTURE_ID is the ID used to created this future FIXME
    """
    session = db.Session.get(session_id)
    future = db.get_user_future(session, user_future_id)
    controller = Controller(executor, executable, session)
    chain_resolve(future, value, controller.run_waiting_machine)
    return controller


def run_new(executor, function, args):
    """Make a new session and run it from the top"""
    session = db.new_session()
    m = db.new_machine(session, args, top_level=True)
    session.save()
    controller = Controller(executor, session)

    controller.run_machine(m.machine_id)
    return controller


def wait_for_finish(
    controller, sleep_interval=0.1, timeout=None,
):
    """Wait for the controller to finish, catching exceptions"""
    try:
        start_time = time.time()
        while not controller.finished:
            time.sleep(sleep_interval)
            if timeout and time.time() - start_time > timeout:
                raise Exception("Timeout waiting for machine to finish")

        # Only relevant for ThreadExecutor currently:
        executor = controller.executor
        if hasattr(executor, "exception") and executor.exception:
            raise Exception from executor.exception.exc_value

        if not all(m.state.stopped for m in controller.machine_data):
            raise Exception("Terminated, but not all machines stopped!")

    except Exception as e:
        warnings.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()
