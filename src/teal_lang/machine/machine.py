"""The Teal virtual machine

To implement closures, just note - a closure is just an unnamed function with
some bindings. Those bindings may be explicit, or not, but are taken from the
current lexical environment. Lexical bindings are introduced by function
definitions, or let-bindings.

"""

import logging
import os
import sys
import time
import traceback
from functools import singledispatchmethod
from io import StringIO
from typing import Any, Dict, List

from ..exceptions import TealError, UserResolvableError, UnexpectedError
from . import types as mt
from .arec import ActivationRecord
from .controller import Controller
from .executable import Executable
from .instruction import Instruction
from .instructionset import *
from .probe import Probe
from .state import State
from .stdout_item import StdoutItem
from .foreign import import_python_function

LOG = logging.getLogger(__name__)


class UnhandledError(UserResolvableError):
    """Unhandled Teal error()"""

    def __init__(self, msg):
        super().__init__(msg, "")


class ForeignError(UserResolvableError):
    """Python code error"""

    def __init__(self, exc):
        info = sys.exc_info()
        tb = "".join(traceback.format_exception(*info))
        super().__init__(str(exc), tb)


def traverse(o, tree_types=(list, tuple)):
    """Traverse an arbitrarily nested list"""
    if isinstance(o, tree_types):
        for value in o:
            for subvalue in traverse(value, tree_types):
                yield subvalue
    else:
        yield o


def shortstr(obj, maxl=20) -> str:
    """Convert an object to string and truncate to a maximum length"""
    s = str(obj)
    return (s[:maxl] + "...") if len(s) > maxl else s


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
        "future": Future,
        "print": Print,
        "sleep": Sleep,
        "atomp": Atomp,
        "nullp": Nullp,
        "list": List,
        "conc": Conc,
        "append": Append,
        "first": First,
        "rest": Rest,
        "length": Length,
        "hash": Hash,
        "get": HGet,
        "set": HSet,
        "nth": Nth,
        "==": Eq,
        "+": Plus,
        # "-": Minus
        "*": Multiply,
        ">": GreaterThan,
        "<": LessThan,
        "&&": OpAnd,
        "||": OpOr,
        "parse_float": ParseFloat,
        "signal": Signal,
        "sid": GetSessionId,
        "tid": GetThreadId,
    }

    def __init__(self, vmid, invoker):
        self._steps = 0
        self.vmid = vmid
        self.invoker = invoker
        self.dc = invoker.data_controller
        self.state = self.dc.get_state(self.vmid)
        self.probe = Probe(self.vmid)
        self.exe = self.dc.executable
        if not self.exe:
            raise UnexpectedError("No executable, can't start thread.")
        self._foreign = {
            name: import_python_function(val.identifier, val.module)
            for name, val in self.exe.bindings.items()
            if isinstance(val, mt.TlForeignPtr)
        }
        LOG.debug("locations %s", self.exe.locations.keys())
        LOG.debug("foreign %s", self._foreign.keys())
        # No entrypoint argument - just set the IP in the state

    @property
    def stopped(self):
        return self.state.stopped

    @property
    def instruction(self):
        return self.exe.code[self.state.ip]

    def step(self):
        """Execute the current instruction and increment the IP"""
        if self.state.ip >= len(self.exe.code):
            raise UnexpectedError("Instruction Pointer out of bounds")
        instr = self.exe.code[self.state.ip]
        self.probe.event(
            "step",
            ip=self.state.ip,
            instr=str(instr),
            ops=str(instr.operands),
            top_of_stack=shortstr(self.state._ds[-3:]),
        )
        self.state.ip += 1  # NOTE - IP incremented before evaluation
        self.evali(instr)
        self._steps += 1  # Counts successfully completed steps

    def run(self):
        """Step through instructions until stopped, or an error occurs

        ERRORS: If one occurs, then:
        - store it in the data controller for analysis later
        - stop execution
        - raise it

        There are two "expected" kinds of errors - a Foreign function error, and
        a Rust "panic!" style error (general error).
        """
        self.probe.event("run")
        broken = False

        self.state.stopped = False
        while not self.state.stopped:
            try:
                self.step()
            except TealError as exc:
                broken = True
                self.state.stopped = True
                self.state.error_msg = str(exc)
                # TODO maybe dump the "core"
                break
            except Exception as exc:
                # It's important to catch *all* errors so that other threads
                # don't continue waiting for this to return.
                broken = True
                self.state.stopped = True
                msg = f"Unexpected Exception:\n\n" + "".join(
                    traceback.format_exception(*sys.exc_info())
                )
                self.state.error_msg = msg
                break

        self.probe.event("stop", steps=self._steps)
        self.dc.set_state(self.vmid, self.state)
        self.dc.set_probe_data(self.vmid, self.probe)
        # This order is important. dc.stop must come last to avoid race
        # conditions in us setting/the user reading the state and probe data
        self.dc.stop(self.vmid, finished_ok=not broken)

    @singledispatchmethod
    def evali(self, i: Instruction):
        """Evaluate instruction"""
        raise NotImplementedError(i)

    @evali.register
    def _(self, i: Bind):
        """Bind the top value on the data stack to a name"""
        ptr = str(i.operands[0])
        try:
            val = self.state.ds_peek(0)
        except IndexError as exc:
            # FIXME this should be a compile time check
            raise UserResolvableError(
                "Missing argument to Bind!",
                "Usually this is because not enough arguments have been passed "
                f"to a function.",
            )
        if not isinstance(val, mt.TlType):
            raise UnexpectedError(f"Bad value to Bind: {val} ({type(val)})")
        self.state.bindings[ptr] = val

    @evali.register
    def _(self, i: PushB):
        """Push the value bound to a name onto the data stack"""
        # The value on the stack must be a Symbol, which is used to find a
        # function to call. Binding precedence:
        #
        # local binding -> exe global bindings -> builtins
        sym = i.operands[0]
        if not isinstance(sym, mt.TlSymbol):
            raise UnexpectedError(str(ValueError(sym, type(sym))))

        ptr = str(sym)
        if ptr in self.state.bindings:
            val = self.state.bindings[ptr]
        elif ptr in self.exe.bindings:
            val = self.exe.bindings[ptr]
        elif ptr in TlMachine.builtins:
            val = mt.TlInstruction(ptr)
        else:
            # FIXME should be a compile time check
            raise UserResolvableError(f"'{ptr}' is not defined", "")

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
    def _(self, i: JumpIf):
        distance = i.operands[0]
        a = self.state.ds_pop()
        # "true" means anything that's not False or Null
        if not isinstance(a, (mt.TlNull, mt.TlFalse)):
            self.state.ip += distance

    @evali.register
    def _(self, i: Return):
        # Only return if there's somewhere to go to, and it's in the same thread
        current_arec = self.dc.pop_arec(self.state.current_arec_ptr)
        if current_arec.dynamic_chain is not None:
            new_arec = self.dc.get_arec(current_arec.dynamic_chain)
            if new_arec.vmid == self.vmid:
                self.probe.event("return")
                self.state.current_arec_ptr = current_arec.dynamic_chain  # the new AR
                self.state.ip = current_arec.call_site + 1
                self.state.bindings = new_arec.bindings
                return

        # Otherwise, this thread has finished!
        self.state.stopped = True
        value = self.state.ds_peek(0)
        self.probe.log(f"Returning value: {shortstr(value)}")
        value, continuations = self.dc.finish(self.vmid, value)
        for machine in continuations:
            self.dc.set_stopped(machine, False)
            # FIXME - invoke all of the machines except the last one. That
            # one, just run in this context. Save one invocation. Caution:
            # tricky with Lambda timeouts.
            self.invoker.invoke(machine)

    @evali.register
    def _(self, i: Call):
        # Arguments for the function must already be on the stack
        num_args = i.operands[0]
        # The value to call will have been retrieved earlier by PushB.
        fn = self.state.ds_pop()

        if isinstance(fn, mt.TlFunctionPtr):
            self.probe.event("call", function=str(fn))
            self.state.bindings = {}
            arec = ActivationRecord(
                function=fn,
                vmid=self.vmid,
                dynamic_chain=self.state.current_arec_ptr,
                call_site=self.state.ip - 1,
                bindings=self.state.bindings,
                ref_count=1,
            )
            self.state.current_arec_ptr = self.dc.push_arec(self.vmid, arec)
            self.state.ip = self.exe.locations[fn.identifier]

        elif isinstance(fn, mt.TlForeignPtr):
            self.probe.event("call_foreign", function=str(fn))
            foreign_f = self._foreign[fn.identifier]
            args = tuple(reversed([self.state.ds_pop() for _ in range(num_args)]))
            # TODO automatically wait for the args? Somehow mark which one we're
            # waiting for in the continuation

            py_args = list(map(mt.to_py_type, args))

            # capture Python's standard output
            sys.stdout = capstdout = StringIO()
            try:
                py_result = foreign_f(*py_args)
            except Exception as e:
                out = capstdout.getvalue()
                self.dc.write_stdout(StdoutItem(self.vmid, out))
                raise ForeignError(e) from e
            finally:
                sys.stdout = sys.__stdout__

            # These aren't included in the finally clause because that really
            # slows down the cleanup
            out = capstdout.getvalue()
            self.dc.write_stdout(StdoutItem(self.vmid, out))

            result = mt.to_teal_type(py_result)
            self.state.ds_push(result)

        elif isinstance(fn, mt.TlInstruction):
            self.probe.event("call_builtin", function=str(fn))
            instr = TlMachine.builtins[fn](num_args)
            self.evali(instr)

        else:
            # FIXME this should be a compile time check
            raise UnexpectedError(f"Don't know how to call `{fn}' of type {type(fn)}.")

    @evali.register
    def _(self, i: ACall):
        # Arguments for the function must already be on the stack
        # ACall can *only* call functions in self.locations (unlike Call)
        num_args = i.operands[0]
        fn_ptr = self.state.ds_pop()

        # FIXME ugh.
        if isinstance(fn_ptr, mt.TlForeignPtr):
            fn_ptr = mt.TlFunctionPtr(f"#F:{fn_ptr.qualified_name}")
        elif not isinstance(fn_ptr, mt.TlFunctionPtr):
            raise UnexpectedError(str(ValueError(fn_ptr)))

        if fn_ptr.identifier not in self.exe.locations:
            # FIXME this should be a compile time check
            raise UserResolvableError(
                f"Can't find function `{fn_ptr}'.", "Does it really exist?"
            )

        args = reversed([self.state.ds_pop() for _ in range(num_args)])
        machine = self.dc.thread_machine(
            self.state.current_arec_ptr, self.state.ip, fn_ptr, args
        )
        self.invoker.invoke(machine)
        future = mt.TlFuturePtr(machine)

        self.probe.event("fork", to_function=fn_ptr.identifier, to_thread=machine)
        self.state.ds_push(future)

    @evali.register
    def _(self, i: Wait):
        val = self.state.ds_peek(0)

        if isinstance(val, mt.TlFuturePtr):
            resolved, result = self.dc.get_or_wait(self.vmid, val)
            if resolved:
                self.probe.log(f"{val} resolved, got {shortstr(result)}")
                self.state.ds_set(0, result)
            else:
                self.probe.log(f"Waiting for {val}")
                # repeat the Wait instruction again:
                #
                # NOTE: Wait cannot be a builtin for this to work! It must be an
                # explicit instruction in the bytecode.
                self.state.ip -= 1
                self.state.stopped = True

        elif isinstance(val, list) and any(
            isinstance(elt, mt.TlFuturePtr) for elt in traverse(val)
        ):
            # The programmer is responsible for waiting on all elements
            # of lists.
            # NOTE - we don't try to detect futures hidden in other
            # kinds of structured data, which could cause runtime bugs!
            raise UserResolvableError(
                "Waiting on a list that contains futures!",
                "For now, you (the programmer) are responsible for waiting on all "
                "elements of structured data. For example, use map and await.",
            )

        else:
            # Not an exception. This can happen if a wait is generated for a
            # normal function call. ie the value already exists.
            pass

    ## "builtins":

    @evali.register
    def _(self, i: Future):
        wrapped = str(self.state.ds_pop())
        plugin_name = str(self.state.ds_pop())

        if self.dc.supports_plugin(plugin_name):
            # Return a Future which can be waited on
            self.probe.event("fork_plugin", plugin=plugin_name, wrapped=wrapped)
            future_id = self.dc.add_plugin_future(plugin_name, wrapped)
            self.state.ds_push(mt.TlFuturePtr(future_id))

        else:
            # Just return the wrapped immediately
            self.probe.log("Skipping call to plugin - controller doesn't support it")
            self.state.ds_push(wrapped)

    @evali.register
    def _(self, i: Atomp):
        val = self.state.ds_pop()
        self.state.ds_push(tl_bool(not isinstance(val, list)))

    @evali.register
    def _(self, i: Nullp):
        val = self.state.ds_pop()
        isnull = isinstance(val, mt.TlNull) or len(val) == 0
        self.state.ds_push(tl_bool(isnull))

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
            # TODO compile time checks...
            raise UserResolvableError(f"b ({b}, {type(b)}) is not a list", "")

        if isinstance(a, mt.TlList):
            self.state.ds_push(mt.TlList(a + b))
        else:
            self.state.ds_push(mt.TlList([a] + b))

    @evali.register
    def _(self, i: Append):
        b = self.state.ds_pop()
        a = self.state.ds_pop()

        a = mt.TlList([]) if isinstance(a, mt.TlNull) else a

        if not isinstance(a, mt.TlList):
            # TODO compile time checks...
            raise UserResolvableError(f"{a} ({type(a)}) is not a list", "")

        self.state.ds_push(mt.TlList(a + [b]))

    @evali.register
    def _(self, i: First):
        lst = self.state.ds_pop()
        if not isinstance(lst, mt.TlList):
            raise UserResolvableError(f"{lst} ({type(lst)}) is not a list", "")
        self.state.ds_push(lst[0])

    @evali.register
    def _(self, i: Rest):
        lst = self.state.ds_pop()
        if not isinstance(lst, mt.TlList):
            raise UserResolvableError(f"{lst} ({type(lst)}) is not a list", "")
        self.state.ds_push(lst[1:])

    @evali.register
    def _(self, i: Nth):
        n = self.state.ds_pop()
        lst = self.state.ds_pop()
        if not isinstance(lst, mt.TlList):
            raise UserResolvableError(f"{lst} ({type(lst)}) is not a list", "")
        self.state.ds_push(lst[n])

    @evali.register
    def _(self, i: Length):
        lst = self.state.ds_pop()
        if not isinstance(lst, mt.TlList):
            raise UserResolvableError(f"{lst} ({type(lst)}) is not a list", "")
        self.state.ds_push(mt.TlInt(len(lst)))

    @evali.register
    def _(self, i: Hash):
        num_args = i.operands[0]
        # convert list [a, b, c, d] (reversed) -> dict {a: b, c: d}
        elts = [self.state.ds_pop() for _ in range(num_args)][::-1]
        pairs = zip(elts[::2], elts[1::2])
        self.state.ds_push(mt.TlHash(pairs))

    @evali.register
    def _(self, i: HGet):
        key = self.state.ds_pop()
        obj = self.state.ds_pop()
        if not isinstance(obj, mt.TlHash):
            raise UserResolvableError(f"{obj} ({type(obj)}) is not a hash", "")
        try:
            res = obj[key]
        except KeyError:
            res = mt.TlNull()
        self.state.ds_push(res)

    @evali.register
    def _(self, i: HSet):
        value = self.state.ds_pop()
        key = self.state.ds_pop()
        obj = self.state.ds_pop()
        if not isinstance(obj, mt.TlHash):
            raise UserResolvableError(f"{obj} ({type(obj)}) is not a hash", "")
        # Create a new object, overwriting the old key
        self.state.ds_push(mt.TlHash({**obj, key: value}))

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
    def _(self, i: Eq):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self.state.ds_push(tl_bool(a == b))

    @evali.register
    def _(self, i: GreaterThan):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self.state.ds_push(tl_bool(a > b))

    @evali.register
    def _(self, i: LessThan):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self.state.ds_push(tl_bool(a < b))

    def _check_bools(self, op, a, b):
        if not isinstance(a, mt.BOOLEANS) or not isinstance(b, mt.BOOLEANS):
            raise UserResolvableError(
                f"Operands to {op} must both be booleans",
                f"Got {a.__tlname__} and {b.__tlname__}",
            )

    @evali.register
    def _(self, i: OpAnd):
        # FIXME no short-circuit behaviour
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self._check_bools("&&", a, b)
        self.state.ds_push(
            tl_bool(isinstance(a, mt.TlTrue) and isinstance(b, mt.TlTrue))
        )

    @evali.register
    def _(self, i: OpOr):
        # FIXME no short-circuit behaviour
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self._check_bools("||", a, b)
        self.state.ds_push(
            tl_bool(isinstance(a, mt.TlTrue) or isinstance(b, mt.TlTrue))
        )

    @evali.register
    def _(self, i: ParseFloat):
        x = self.state.ds_pop()
        self.state.ds_push(mt.TlFloat(float(x)))

    @evali.register
    def _(self, i: Sleep):
        t = self.state.ds_peek(0)
        time.sleep(t)

    @evali.register
    def _(self, i: Print):
        # Leave the value in the stack - print() 'returns' the value printed
        val = self.state.ds_peek(0)
        # This should take a vmid - data stored is a tuple (vmid, str)
        # Could also store a timestamp...
        self.dc.write_stdout(StdoutItem(self.vmid, str(val) + "\n"))

    @evali.register
    def _(self, i: Signal):
        msg = self.state.ds_peek(0)
        val = self.state.ds_peek(1)
        self.dc.write_stdout(StdoutItem(self.vmid, f"\n[signal {val}]: {msg}\n"))
        if str(val) == "error":
            raise UnhandledError(msg)
        # other kinds of signals don't need special handling

    @evali.register
    def _(self, i: GetSessionId):
        self.state.ds_push(mt.TlString(self.dc.session_id))

    @evali.register
    def _(self, i: GetThreadId):
        self.state.ds_push(mt.TlInt(self.vmid))

    def __repr__(self):
        return f"<Machine {id(self)}>"


def tl_bool(val):
    """Make a Teal bool-ish from val"""
    if val not in (True, False):
        raise UnexpectedError(str(ValueError(val)))
    return mt.TlTrue() if val is True else mt.TlFalse()


def new_number_type(a, b):
    """The number type to use on operations of two numbers"""
    if isinstance(a, mt.TlFloat) or isinstance(b, mt.TlFloat):
        return mt.TlFloat
    else:
        return mt.TlInt
