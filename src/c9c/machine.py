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

from dataclasses import dataclass
from functools import singledispatchmethod
from typing import Any, Dict, List

from . import lang as l


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
    """Wait until the Nth item on the stack has resolved. May terminate"""

    op_types = [int]


class MFCall(I):
    """Call a *foreign* function"""

    op_types = [callable, int]


class Return(I):
    """Return to the call site"""


# This is the /application/ of a function - first arg on the stack must
# /evaluate to/ a Func, which is the /reference to/ a function.
class Call(I):
    """Call a function (sync)"""

    op_types = [int]


class ACall(I):
    """Call a function (async)"""

    op_types = [int]


# I think we'll need a "stream" datatype


################################################################################
## The Machine


class State:
    """Entirely represent the state of a machine execution."""


class Runtime:
    """Implement the parts of execution that require external interaction"""


@dataclass
class Continuation:
    state: State


@dataclass
class Executable:
    locations: dict
    code: list
    name: str


class C9Machine:
    """This is the Machine, the CPU.

    There is one Machine per compute node. There may be multiple compute nodes.

    The stacks are nested deques. This only matters for async stuff - the async
    bit gets entirely new memory (with args on the stack) and a Continuation.
    The continuation contains a pointer to the old memory (state), and the IP.

    When run normally, the Machine starts executing instructions from the
    beginning until the instruction pointer reaches the end.

    """

    count = 0

    def __init__(
        self, executable: Executable, state: State, runtime: Runtime, *, probe=None,
    ):
        C9Machine.count += 1
        self.m_id = C9Machine.count
        self.imem = executable.code
        self.locations = executable.locations
        self.state = state
        self.runtime = runtime
        self.probe = probe
        # No entrypoint argument - just set the IP in the state

    @property
    def stopped(self):
        return self.state.stopped

    @property
    def instruction(self):
        return self.imem[self.state.ip]

    @property
    def terminated(self):
        return self.state.ip == len(self.imem)

    def step(self):
        """Execute the current instruction and increment the IP"""
        assert self.state.ip <= len(self.imem)
        if self.terminated:
            self.state.stopped = True
            return
        if self.probe:
            self.probe.step_cb(self)
        instr = self.instruction
        self.state.ip += 1
        self.evali(instr)

    def run(self):
        while not self.stopped:
            self.step()
        if self.probe:
            self.probe.on_stopped(self)
        self.runtime.on_stopped(self)

    @singledispatchmethod
    def evali(self, i: Instruction):
        """Evaluate instruction"""
        raise NotImplementedError()

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

    @evali.register
    def _(self, i: Return):
        try:
            self.state.es_return()
        except IndexError:
            self.runtime.on_terminated(self)
            self.state.stopped = True
        # self.state.pop_ds()
        # self.state.pop_ip()
        # self.state.pop_bindings()

    @evali.register
    def _(self, i: Call):
        # Arguments for the function must already be on the stack
        num_args = i.operands[0]
        name = self.state.ds_pop()
        # args = [self.state.ds_pop() for _ in range(num_args)]
        # self.state.push_ds(args)
        # self.state.push_ip(self.locations[name])
        # self.state.push_bindings({})
        self.state.es_enter(self.locations[name])

    @evali.register
    def _(self, i: ACall):
        # Arguments for the function must already be on the stack
        num_args = i.operands[0]
        name = self.state.ds_pop()
        args = reversed([self.state.ds_pop() for _ in range(num_args)])
        result = self.runtime.fork(self, name, args)
        self.state.ds_push(result)

    @evali.register
    def _(self, i: MFCall):
        func = i.operands[0]
        num_args = i.operands[1]
        args = reversed([self.state.ds_pop() for _ in range(num_args)])
        # TODO convert args to python values???
        # result = self.runtime.fcall(func, args)
        result = func(*args)
        self.state.ds_push(result)

    @evali.register
    def _(self, i: Wait):
        offset = i.operands[0]
        val = self.state.ds_peek(offset)

        if self.runtime.maybe_wait(self, offset):
            self.state.stopped = True

        elif isinstance(val, list):
            for elt in traverse(val):
                if self.runtime.is_future(elt):
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

    def __repr__(self):
        return f"<Machine M{self.m_id}>"


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


class MaxStepsReached(Exception):
    """Max Execution steps limit reached"""


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


def print_instructions(exe: Executable):
    print(" /")
    for i, instr in enumerate(exe.code):
        if i in exe.locations.values():
            funcname = next(k for k in exe.locations.keys() if exe.locations[k] == i)
            print(f" | ;; {funcname}:")
        print(f" | {i:4} | {instr}")
    print(" \\")


if __name__ == "__main__":
    raise Exception("Don't run this file - import it")
