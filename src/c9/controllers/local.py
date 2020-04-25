"""Local Implementation"""
import importlib
import concurrent.futures
from functools import singledispatchmethod
import logging
import sys
import threading
import time
import traceback
import warnings

from ..machine import C9Machine
from ..machine.controller import Controller as BaseController
from ..machine.future import ChainedFuture
from ..machine.state import State
from ..machine.probe import Probe
from ..machine import c9e
from ..machine.instruction import Instruction
from ..machine.executable import Executable
from ..machine import instructionset as mi

# https://docs.python.org/3/library/logging.html#logging.basicConfig
LOG = logging.getLogger(__name__)


class Probe(Probe):
    """A monitoring probe that stops the VM after a number of steps"""

    count = 0

    def __init__(self, *, max_steps=500):
        self._max_steps = max_steps
        self._step = 0
        Probe.count += 1
        self._name = f"P{Probe.count}"
        self.logs = []
        self.early_stop = False

    def log(self, text):
        self.logs.append(f"*** <{self._name}> {text}")

    def on_enter(self, m, fn_name: str):
        self.log(f"===> {fn_name}")

    def on_return(self, m):
        self.log(f"<===")

    def on_step(self, m):
        self._step += 1
        preface = f"[step={self._step}, ip={m.state.ip}] {m.instruction}"
        data = list(m.state._ds)
        self.log(f"{preface:40.40} | {data}")
        # self.logs.append("Data: " + str(tuple(m.state._ds)))
        if self._step >= self._max_steps:
            self.log(f"MAX STEPS ({self._max_steps}) REACHED!! ***")
            self.early_stop = True
            m._stopped = True

    def on_stopped(self, m):
        kind = "Terminated" if m.terminated else "Stopped"
        self.logs.append(f"*** <{self._name}> {kind} after {self._step} steps. ***")
        self.logs.append(m.state.to_table())


class LocalFuture(ChainedFuture):
    def __init__(self, controller):
        self.lock = threading.Lock()
        self.continuations = []
        self.chain = None
        self.resolved = False
        self.value = None
        self.controller = controller

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"


class DataController:
    def __init__(self):
        # NOTE - could make probes optional, but why?!
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self.machine_output = {}
        self.executable = None
        self._top_level_vmid = None
        self.result = None
        self.finished = False

    def new_machine(self, args, fn_name, is_top_level=False):
        if fn_name not in self.executable.locations:
            raise Exception(f"Function `{fn_name}` doesn't exist")
        future = LocalFuture(self)
        probe = Probe()
        state = State(*args)
        state.ip = self.executable.locations[fn_name]
        vmid = self._machine_idx
        self._machine_idx += 1
        self._machine_future[vmid] = future
        self._machine_state[vmid] = state
        self._machine_probe[vmid] = probe
        self.machine_output[vmid] = []
        if is_top_level:
            if self._top_level_vmid:
                raise Exception("Already got a top level!")
            self._top_level_vmid = vmid
        return vmid

    def is_top_level(self, vmid):
        return vmid == self._top_level_vmid

    def finish(self, vmid, result):
        # in other implementations, could sync state
        if self.is_top_level(vmid):
            self.result = result
            self.finished = True

    def get_result_future(self, vmid):
        return self._machine_future[vmid]

    def get_state(self, vmid):
        return self._machine_state[vmid]

    def get_probe(self, vmid):
        return self._machine_probe[vmid]

    def set_ds_value(self, vmid, offset, value):
        state = self.get_state(vmid)
        state.ds_set(offset, value)

    def restart(self, vmid):
        state = self.get_state(vmid)
        state.stopped = False

    def get_or_wait(self, vmid, future, offset):
        # prevent race between resolution and adding the continuation
        with future.lock:
            resolved = future.resolved
            if resolved:
                value = future.value
            else:
                future.continuations.append((vmid, offset))
                value = None
        return resolved, value

    def is_future(self, val):
        return isinstance(val, LocalFuture)

    @property
    def machines(self):
        return list(self._machine_future.keys())

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]

    @property
    def outputs(self):
        return list(self.machine_output.values())


class ThreadInvoker:
    def __init__(self, data_controller, evaluator_cls):
        self.data_controller = data_controller
        self.evaluator_cls = evaluator_cls
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def invoke(self, vmid):
        m = C9Machine(vmid, self)
        thread = threading.Thread(target=m.run)
        thread.start()


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
        self.data_controller.machine_output[self.vmid].append((time.time(), str(val)))

    @evali.register
    def _(self, i: mi.Future):
        raise NotImplementedError


class Interface:
    def __init__(self, data_controller, invoker):
        self.invoker = invoker
        self.data_controller = data_controller
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

    def _add_def(self, name, code):
        # If any machines are running, they will break!
        LOG.info("Defining `%s` (%d instructions)", name, len(code))
        self.defs[name] = code

    def _importpy(self, dest_name, mod_name, fn_name):
        LOG.info("Importing `%s` from %s", fn_name, mod_name)
        self.foreign[dest_name] = (fn_name, mod_name)

    def set_toplevel(self, toplevel):
        for name, code in toplevel.defs.items():
            self._add_def(name, code)

        for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
            self._importpy(dest_name, mod_name, fn_name)

        exe = self._build_exe()
        self.data_controller.executable = exe

    def callf(self, name, args):
        LOG.info("Calling `%s`", name)
        m = self.data_controller.new_machine(args, name, is_top_level=True)
        self.invoker.invoke(m)

    def resume(self, name, code):
        # not relevant locally?
        raise NotImplementedError
