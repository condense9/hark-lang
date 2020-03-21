# Machine
# - Storage
# - Evaluation
#
# Push/pop values (by name)
# MFCall a particular system operation
# OR, Call a peripheral method

# Program
# - System Operations (uniquely identifiable, peripheral operations)
# - Code


# Deployment
#
# - Set up the peripherals required (if the Program includes Docker, set up ECS)
# -


# Peripheral
#   call method
import time

from dataclasses import dataclass
from functools import singledispatchmethod
from typing import Any, Dict, List
import lang as l


def traverse(o, tree_types=(list, tuple)):
    """Traverse an arbitrarily nested list"""
    if isinstance(o, tree_types):
        for value in o:
            for subvalue in traverse(value, tree_types):
                yield subvalue
    else:
        yield o


class Instruction:
    op_types = []
    check_op_types = True

    def __init__(self, *operands):
        good_length = len(operands) == len(self.op_types)
        # this is horrible:
        good_types = all(
            [
                callable(a) if b == callable else isinstance(a, b)
                for a, b in zip(operands, self.op_types)
            ]
        )
        if self.check_op_types and not (good_length and good_types):
            raise Exception(f"Bad operands - {operands}")
        self.operands = operands

    def __repr__(self):
        name = type(self).__name__.upper()
        ops = " ".join(map(str, self.operands))
        return f"{name:8} {ops}"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )


################################################################################
## Instruction Set

I = Instruction


# Synchronous can be implemented on top of async. Therefore, there is no "jump
# to function" instruction. Actually, that's not true. What does the machine do?
# Execute something now (sync), or wait (basically stop)?
# class Call(I):
#     """Call a (named) function asynchronously"""


class Jump(I):
    """Move execution to a different point, relative to the current point"""

    op_types = [int]


class JumpIE(I):
    """Relative jump, only if top two elements on the stack are equal"""

    op_types = [int]


# TODO class JumpLong ?


class Perphhhhh(I):
    """We need an instruction to call 'into' peripherals.

    Peripherals need some way of registering (?)...

    """


class Bind(I):
    """Take the top value off the stack and bind it to a register"""

    op_types = [int]


class PushV(I):
    """Push an immediate value onto the stack"""

    op_types = [object]


class PushB(I):
    """Push a bound value onto the stack"""

    op_types = [int]


class Pop(I):
    """Remove top value from the stack and discard it"""


class Wait(I):
    """Wait until the top item on the stack has resolved. May terminate"""


class MFCall(I):
    """Call a *foreign* function *asynchronously*"""

    op_types = [callable, int]


class Return(I):
    """Return to the call site"""


class Fork(I):
    """Like Call, but split the stack and allow a continuation from this point"""


# This is the /application/ of a function - first arg must /evaluate to/ a Func,
# which is the /reference to/ a function.
# TODO - why is this a Builtin, not a machine Instruction?
class Call(I):
    """Call a function (sync)"""


# I think we'll need a "stream" datatype


################################################################################
## The Machine


class State:
    pass  # Implemented per backend. TODO abstracts?


@dataclass
class Continuation:
    state: State


@dataclass
class Executable:
    locations: dict
    code: list


class M:
    """This is the Machine, the CPU.

    There is one Machine per compute node. There may be multiple compute nodes.

    The stacks are nested deques. This only matters for async stuff - the async
    bit gets entirely new memory (with args on the stack) and a Continuation.
    The continuation contains a pointer to the old memory (state), and the IP.

    When run normally, the Machine starts executing instructions from the
    beginning until the instruction pointer reaches the end.

    """

    def __init__(
        self, executable: Executable, state: State, probe=None,
    ):
        self.imem = executable.code
        self.locations = executable.locations
        self.state = state
        self.probe = probe
        self.state.ip = 0
        self._stopped = False

    @property
    def stopped(self):
        return self._stopped

    @property
    def instruction(self):
        return self.imem[self.state.ip]

    def step(self):
        assert self.state.ip < len(self.imem)
        if self.probe:
            self.probe.step_cb(self)
        instr = self.instruction
        self.state.ip += 1
        self.evali(instr)
        if self.state.ip == len(self.imem):
            self._stopped = True

    def print_instructions(self):
        print(" /")
        for i, instr in enumerate(self.imem):
            if i in self.locations.values():
                funcname = next(
                    k for k in self.locations.keys() if self.locations[k] == i
                )
                print(f" | ;; {funcname}:")
            print(f" | {i:4} | {instr}")
        print(" \\")

    def run(self):
        while not self.stopped:
            self.step()

    @singledispatchmethod
    def evali(self, i: Instruction):
        raise NotImplementedError()

    @evali.register
    def _(self, i: MFCall):
        func = i.operands[0]
        argcount = i.operands[1]
        args = [self.state.ds_pop() for _ in range(argcount)]
        # TODO convert args to python values???
        result = self._fcall(func, args)
        # result = func(*args)
        self.state.ds_push(result)

    @evali.register
    def _(self, i: Wait):
        val = self.state.ds_peek()
        # TODO per-backend tpyes? How? A separate types module?
        if self._is_future(val):
            self._wait_for(val)
        elif isinstance(val, list):
            for elt in traverse(val):
                if self._is_future(elt):
                    # The programmer is responsible for waiting on VLists
                    raise Exception("Waiting on a VList that contains futures!")
        else:
            # Not an exception. This can happen if a wait is generated for a
            # normal function call. ie the value already exists.
            # raise Exception("Waiting on something already used")
            pass

    @evali.register
    def _(self, i: Return):
        self.state.es_return()

    @evali.register
    def _(self, i: Bind):
        ptr = i.operands[0]
        val = self.state.ds_pop()
        assert isinstance(ptr, int)
        self.state.set_bind(ptr, val)

    @evali.register
    def _(self, i: PushB):
        ptr = i.operands[0]
        val = self.state.get_bind(ptr)
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

    ## "builtins":

    @evali.register
    def _(self, i: Call):
        # Arguments for the function must already be on the stack
        name = self.state.ds_pop()
        self.state.es_enter(self.locations[name])

    @evali.register
    def _(self, i: l.Atomp):
        val = self.state.ds_pop()
        self.state.ds_push(not isinstance(val, list))

    @evali.register
    def _(self, i: l.Nullp):
        val = self.state.ds_pop()
        self.state.ds_push(len(val) == 0)

    @evali.register
    def _(self, i: l.Cons):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        if isinstance(a, list):
            assert not isinstance(b, list)
            self.state.ds_push(a + [b])
        else:
            self.state.ds_push([a, b])

    @evali.register
    def _(self, i: l.Car):
        lst = self.state.ds_pop()
        self.state.ds_push(lst[0])

    @evali.register
    def _(self, i: l.Cdr):
        lst = self.state.ds_pop()
        self.state.ds_push(lst[1:])

    @evali.register
    def _(self, i: l.Eq):
        a = self.state.ds_pop()
        b = self.state.ds_pop()
        self.state.ds_push(a == b)


# Foreign function calls produce futures. This allows evaluation to continue. We
# assume that they are "long-running".
#
# When a MFCall is encountered, there are two options:
# - block until there is compute resource to evaluate it
# - submit it for evaluation (local or remote), returning a future
#
# So FCalls always return Futures. Also, when an MFCall is made, the arguments
# must be resolved. They are removed from the stack and replaced with a future.
#
# The Future returned by an MFCall can be passed around on the stack, and can be
# waited upon. Each future can only be Waited on once. The resolved future can
# of course be passed around. Actually maybe not - you can have multiple
# continuations, and you continue them in the same way as performing an fcall.
#
# When an MFCall finishes, it resolves the future. If there is a continuation for
# that future (ie something else Waited on it), then execution is continued from
# that point.
#
# To continue execution, the IP, stack, and bindings must be retrieved.
#
# When a Call is encountered, it is evaluated immediately. It may modify the
# stack (from the caller's point of view).
#
# Actually, there are Calls and ACalls, and FCalls are a special type of ACall
# (or Call!). The arguments to FCalls must be resolved, but the arguments to
# ACalls don't need to be (they can Wait).
#
# When a Wait is encountered, there are two options:
# - if the future has already resolved, continue
# - otherwise, save a continuation and terminate
#
# When  MFCall finishes, two options:
# - if a continuation exists, go there
# - otherwise, terminate
#
# When Return from (sync) Call is encountered, restore previous bindings and
# stack, and jump back


################################################################################
## Local Implementation

import concurrent.futures
from collections import deque

Future = concurrent.futures.Future


# "State" must be implemented per backend.
class LocalState(State):
    def __init__(self, *values):
        self._bindings = {}  # ........ current bindings
        self._bs = deque()  # ......... binding stack
        self._ds = deque(values)  # ... data stack
        self._es = deque()  # ......... execution stack
        self.ip = 0

    def set_bind(self, ptr, value):
        self._bindings[ptr] = value

    def get_bind(self, ptr):
        return self._bindings[ptr]

    def ds_push(self, val):
        self._ds.append(val)

    def ds_pop(self):
        return self._ds.pop()

    def ds_peek(self):
        return self._ds[-1]

    def es_enter(self, new_ip):
        self._es.append(self.ip)
        self.ip = new_ip
        self._bs.append(self._bindings)
        self._bindings = {}

    def es_return(self):
        self.ip = self._es.pop()
        self._bindings = self._bs.pop()

    def restore(self, m):
        self._bindings = m._bindings
        self._bs = m._bs
        self._ds = m._ds
        self._es = m._es
        self.ip = m.ip

    def show(self):
        print("Bind: " + ", ".join(f"{k}->{v}" for k, v in self._bindings.items()))
        print(f"Data: {self._ds}")
        print(f"Eval: {self._es}")


# Ignore builtins for now. Not necessary. MFCall (and maybe Map) is the only one
# that would need to be implementation-defined.
#
# So no custom "microcode" for now. 03/12/20


class LocalMachine(M):
    """The local machine is special, as it can manage concurrency locally

    It has the ability to "pause", while some computation completes.

    """

    def __init__(self, *args, max_workers=2, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._paused = False

    def _is_future(self, val):
        return isinstance(val, concurrent.futures.Future)

    def _fcall(self, func, args) -> Future:
        """Call func(args) asynchronously, returning a future"""
        return self._executor.submit(func, *args)

    def _wait_for(self, future):
        c = Continuation(self.state)
        # When the given future resolves, continue execution from c
        def cont(_):
            self.state.restore(c.state)
            # When future resolves, continue execution from c, but with the
            # resolved value on the stack
            fut = self.state.ds_pop()
            assert fut == future
            # TODO convert args to python values???
            self.state.ds_push(fut.result())
            self._paused = False

        # Pause the local machine - it's waiting for a future to resolve, and
        # can't do anything else. This is a bit lame, and doesn't use the
        # ThreadPoolExecutor correctly - there might only be one future pending,
        # but we still block here.
        self._paused = True
        future.add_done_callback(cont)

    def run(self):
        while not self.stopped:
            if self._paused:
                time.sleep(1)
            else:
                self.step()


class MaxStepsReached(Exception):
    """Max Execution steps limit reached"""


class DebugProbe:
    """A monitoring probe that stops the VM after a number of steps"""

    def __init__(self, *, trace=True, max_steps=300):
        self._max_steps = max_steps
        self._trace = trace
        self._step = 0

    def step_cb(self, m):
        self._step += 1
        if self._trace:
            print(f"*** [step={self._step}, ip={m.state.ip}] {m.instruction}")
            m.state.show()
            print("")  # newline
        if self._step >= self._max_steps:
            print(f"*** MAX STEPS ({self._max_steps}) REACHED!! ***")
            raise MaxStepsReached()


# Call or MFCall: push values onto stack. Result will be top value on the stack
# upon return. This is ok because the stack isn't shared.
#
# CallA or RunA: I don't think RunA needs to be implemented. It can be wrapped
# with CallA. CallA creates a new machine that starts at the given function, and
# resolves the future at the top of the stack. When the future resolves, it
# jumps back to the caller, with the caller stack.
#
# Function defintions themselves don't have to be "sync" or "async". CallA just
# fills in the extra logic in the implementation. This is a CISC-style approach.


# Programming the VM with other languages
#
# Build a minimal "parser" - read a text file of assembly line by line. All
# operands are numbers or strings. Then, to run it, provide an "environment"
# (dict) of foreign functions that the machine can call. So a JS frontend can
# work just like the python one - it just needs to compile right, and provide
# the env.


# MFCall runs something in *Python* syncronously. It takes a function, and a
# number of arguments, and literally calls it. This function may be a type
# constructor from a language point of view, or not. It may return a Future. The
# machine knows how to wait for Futures.
#
# This allows "async execution" to be entirely implementation defined. The
# machine has no idea how to do it. It knows how to handle the result though. So
# it's becoming more like a very simple Forth-style stack machine. Be careful,
# either approach could work - pick one. Forth: very flexible, but more complex.
# Builtins: less flexible, but simpler.


if __name__ == "__main__":
    raise Exception("Don't run this file - import it")
