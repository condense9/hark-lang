"""The Teal virtual machine

To implement closures, just note - a closure is just an unnamed function with
some bindings. Those bindings may be explicit, or not, but are taken from the
current lexical environment. Lexical bindings are introduced by function
definitions, or let-bindings.

"""

import importlib
import logging
import time
from functools import singledispatchmethod
from typing import Any, Dict, List

from . import types as mt
from .controller import Controller
from .executable import Executable
from .instruction import Instruction
from .instructionset import *
from .probe import Probe
from .state import State

LOG = logging.getLogger(__name__)


class ImportPyError(Exception):
    """Error importing some code from Python"""


def traverse(o, tree_types=(list, tuple)):
    """Traverse an arbitrarily nested list"""
    if isinstance(o, tree_types):
        for value in o:
            for subvalue in traverse(value, tree_types):
                yield subvalue
    else:
        yield o


def import_python_function(fnname, modname):
    """Load function

    If modname is None, fnname is taken from __builtins__ (e.g. 'print')

    PYTHONPATH must be set up already.
    """
    if modname:
        spec = importlib.util.find_spec(modname)
        if not spec:
            raise ImportPyError(f"Could not find module `{modname}`")
        m = spec.loader.load_module()
    else:
        m = __builtins__
    fn = getattr(m, fnname)
    LOG.debug("Loaded %s", fn)
    return fn


class TlMachine:
    """Virtual Machine to execute Teal bytecode.

    The machine operates in the context of a Controller. There may be multiple
    machines connected to the same controller. All machines share the same
    executable, defined by the controller.

    There is one Machine per compute node. There may be multiple compute nodes.

    When run normally, the Machine starts executing instructions from the
    beginning until the instruction pointer reaches the end.

    """

    builtins = {
        "print": Print,
        "sleep": Sleep,
        "=": Eq,
        "atomp": Atomp,
        "nullp": Nullp,
        "list": List,
        "conc": Conc,
        "first": First,
        "rest": Rest,
        "wait": Wait,
        "future": Future,
        "+": Plus,
        # "-": Minus
        "*": Multiply,
        "nth": Nth,
    }

    def __init__(self, vmid, invoker):
        self.vmid = vmid
        self.invoker = invoker
        self.data_controller = invoker.data_controller
        self.state = self.data_controller.get_state(self.vmid)
        self.probe = self.data_controller.get_probe(self.vmid)
        self.exe = self.data_controller.executable
        self.evaluator = self.data_controller.evaluator_cls(self)
        self._foreign = {
            name: import_python_function(fn, mod)
            for name, (fn, mod) in self.exe.foreign.items()
        }
        LOG.debug("locations %s", self.exe.locations.keys())
        LOG.debug("foreign %s", self.exe.foreign.keys())
        # No entrypoint argument - just set the IP in the state

    @property
    def stopped(self):
        return self.state.stopped

    @property
    def terminated(self):
        """Run out of instructions to execute"""
        return self.state.ip == len(self.exe.code)

    @property
    def instruction(self):
        return self.exe.code[self.state.ip]

    def step(self):
        """Execute the current instruction and increment the IP"""
        assert self.state.ip < len(self.exe.code)
        self.probe.on_step(self)
        instr = self.exe.code[self.state.ip]
        self.state.ip += 1
        self.evali(instr)
        if self.terminated:
            self.state.stopped = True

    def run(self):
        self.probe.on_run(self)
        while not self.stopped:
            self.step()
        self.probe.on_stopped(self)

    @singledispatchmethod
    def evali(self, i: Instruction):
        """Evaluate instruction"""
        assert isinstance(i, Instruction)
        self.evaluator.evali(i)

    @evali.register
    def _(self, i: Bind):
        ptr = i.operands[0]
        val = self.state.ds_pop()
        self.state.set_bind(ptr, val)

    @evali.register
    def _(self, i: PushB):
        # The value on the stack must be a Symbol, which is used to find a
        # function to call. Binding precedence:
        #
        # local value -> functions -> foreigns -> builtins
        sym = i.operands[0]
        if not isinstance(sym, mt.TlSymbol):
            raise ValueError(sym, type(sym))

        ptr = str(sym)
        if ptr in self.state.bound_names:
            val = self.state.get_bind(ptr)
        elif ptr in self.exe.locations:
            val = mt.TlFunction(ptr)
        elif ptr in self._foreign:
            val = mt.TlForeign(ptr)
        elif ptr in TlMachine.builtins:
            val = mt.TlInstruction(ptr)
        else:
            raise Exception(f"Nothing bound to {ptr}")

        self.state.ds_push(val)

    @evali.register
    def _(self, i: PushV):
        val = i.operands[0]
        self.state.ds_push(val)

    @evali.register
    def _(self, i: Pop):
        self.state.ds_pop()

    @evali.register
    def _(self, i: Jump):
        distance = i.operands[0]
        self.state.ip += distance

    @evali.register
    def _(self, i: JumpIE):
        distance = i.operands[0]
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        if a == b:
            self.state.ip += distance

    @evali.register
    def _(self, i: Return):
        if self.state.can_return():
            self.probe.on_return(self)
            self.state.es_return()
        else:
            self.state.stopped = True
            value = self.state.ds_peek(0)
            LOG.info(f"{self.vmid} Returning value: {value}")
            value, continuations = self.data_controller.finish(self.vmid, value)
            for machine in continuations:
                self.probe.log(
                    f"{self.vmid}: setting machine {machine} value to {value}"
                )
                self.data_controller.set_future_value(machine, 0, value)
                self.invoker.invoke(machine)

    @evali.register
    def _(self, i: Call):
        # Arguments for the function must already be on the stack
        num_args = i.operands[0]
        # The value to call will have been retrieved earlier by PushB.
        fn = self.state.ds_pop()
        self.probe.on_enter(self, fn)

        if isinstance(fn, mt.TlFunction):
            self.state.es_enter(self.exe.locations[fn])

        elif isinstance(fn, mt.TlForeign):
            foreign_f = self._foreign[fn]
            args = tuple(reversed([self.state.ds_pop() for _ in range(num_args)]))
            self.probe.log(f"{self.vmid}--> {foreign_f} {args}")
            # TODO automatically wait for the args? Somehow mark which one we're
            # waiting for in the continuation

            py_args = map(mt.to_py_type, args)
            py_result = foreign_f(*py_args)
            result = mt.to_teal_type(py_result)

            self.state.ds_push(result)

        elif isinstance(fn, mt.TlInstruction):
            instr = TlMachine.builtins[fn](num_args)
            self.evali(instr)

        else:
            raise Exception(f"Don't know how to call {fn} ({type(fn)})")

    @evali.register
    def _(self, i: ACall):
        # Arguments for the function must already be on the stack
        # ACall can *only* call functions in self.locations (unlike Call)
        num_args = i.operands[0]
        fn_name = self.state.ds_pop()
        args = reversed([self.state.ds_pop() for _ in range(num_args)])

        machine = self.data_controller.new_machine(args, fn_name)
        self.invoker.invoke(machine)
        future = mt.TlFuturePtr(machine)

        self.probe.log(f"Fork {self} => {future}")
        self.state.ds_push(future)

    @evali.register
    def _(self, i: Wait):
        offset = 0  # TODO cleanup - no more offset!
        val = self.state.ds_peek(offset)

        if isinstance(val, mt.TlFuturePtr):
            resolved, result = self.data_controller.get_or_wait(
                self.vmid, val, self.state, self.probe
            )
            if resolved:
                LOG.info(f"{self.vmid} Finished waiting for {val}, got {result}")
                self.state.ds_set(offset, result)
            else:
                LOG.info(f"{self.vmid} waiting for {val}")
                assert self.state.stopped

        elif isinstance(val, list) and any(
            isinstance(elt, mt.TlFuturePtr) for elt in traverse(val)
        ):
            # The programmer is responsible for waiting on all elements
            # of lists.
            # NOTE - we don't try to detect futures hidden in other
            # kinds of structured data, which could cause runtime bugs!
            raise Exception("Waiting on a list that contains futures!")

        else:
            # Not an exception. This can happen if a wait is generated for a
            # normal function call. ie the value already exists.
            pass

    ## "builtins":

    @evali.register
    def _(self, i: Atomp):
        val = self.state.ds_pop()
        self.state.ds_push(not isinstance(val, list))

    @evali.register
    def _(self, i: Nullp):
        val = self.state.ds_pop()
        self.state.ds_push(len(val) == 0)

    @evali.register
    def _(self, i: List):
        num_args = i.operands[0]
        elts = [self.state.ds_pop() for _ in range(num_args)]
        self.state.ds_push(mt.TlList(reversed(elts)))

    @evali.register
    def _(self, i: Conc):
        b = self.state.ds_pop()
        a = self.state.ds_pop()

        # Null is interpreted as the empty list for b
        b = mt.TlList([]) if isinstance(b, mt.TlNull) else b

        if not isinstance(b, mt.TlList):
            raise Exception(f"b ({b}, {type(b)}) is not a list")

        if isinstance(a, mt.TlList):
            self.state.ds_push(mt.TlList(a + b))
        else:
            self.state.ds_push(mt.TlList([a] + b))

    @evali.register
    def _(self, i: First):
        lst = self.state.ds_pop()
        self.state.ds_push(lst[0])

    @evali.register
    def _(self, i: Rest):
        lst = self.state.ds_pop()
        self.state.ds_push(lst[1:])

    @evali.register
    def _(self, i: Eq):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self.state.ds_push(make_bool(a == b))

    @evali.register
    def _(self, i: Plus):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        cls = new_number_type(a, b)
        self.state.ds_push(cls(a + b))

    @evali.register
    def _(self, i: Multiply):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        cls = new_number_type(a, b)
        self.state.ds_push(cls(a * b))

    @evali.register
    def _(self, i: Sleep):
        t = self.state.ds_peek(0)
        time.sleep(t)

    def __repr__(self):
        return f"<Machine {id(self)}>"


def make_bool(val):
    """Make a Teal bool-ish from val"""
    # Do we need two bool types (true/false)? Is Null/nil enough?
    return mt.TlTrue() if val is True else mt.TlNull()


def new_number_type(a, b):
    """The number type to use on operations of two numbers"""
    if isinstance(a, mt.TlFloat) or isinstance(b, mt.TlFloat):
        return mt.TlFloat
    else:
        return mt.TlInt
