"""This implements a minimal language embedded in Python

Capabilities
- first-class functions
- branching
- native python value handling
- foreign function calling

"""
import inspect
import itertools
from collections import deque
from dataclasses import dataclass
from functools import singledispatch, wraps
from typing import List


class Node:
    """The language is built from nodes (it's a DAG)

    Nodes are expressions to be evaluated. Children are "sub-expressions" that
    must be evaluated first (arguments). Sub-expressions may be shared between
    nodes.

    There are a few primitives (values that evaluate to themselves, and are not
    parameterised): Symbols, Numbers, Strings, TODO...

    All leaf nodes are primitives (no parameters/children).

    """

    _count = 0  # Total node count to assign unique names

    def __init__(self, *operands):
        Node._count += 1
        self._name = f"N{Node._count}"
        self.operands = [Quote(o) if not isinstance(o, Node) else o for o in operands]

    @property
    def name(self):
        return self._name

    @property
    def descendents(self) -> list:
        """Get all descendent nodes"""
        operand_descendents = [[n] + n.descendents for n in self.operands]
        return list(itertools.chain.from_iterable(operand_descendents))

    def __repr__(self):
        kind = type(self).__name__
        return f"<{kind} {self.name}>"

    def __eq__(self, other):
        return type(self) == type(other) and all(
            a == b for a, b in zip(self.operands, other.operands)
        )


class Symbol(Node):
    """A symbolic value

    NOTE that these are not implemented as "proper" symbols in the machine, but
    are scoped to the current function.

    """

    def __init__(self, name):
        super().__init__(name)
        self.symbol_name = name

    @property
    def descendents(self):
        return []


class Quote(Node):
    """Represent a literal/primitive value"""

    def __init__(self, value):
        super().__init__()
        # Set operands manually - don't pass in to super().__init__ because it
        # will try to create a Quote, which will try to... etc
        self.value = value
        # TODO check allowed operand types - check that there are no references
        # to other nodes (a quote is *literal* data).

    def unquote(self):
        """Get the machine representation of the value"""
        return self.value

    @property
    def descendents(self):
        return []

    def __eq__(self, other):
        return isinstance(other, Quote) and self.unquote() == other.unquote()


class Func(Quote):
    """Represents a function - a DAG with symbolic bindings for values

    NOTE that this is a Quote! That is, a literal value.
    """

    blocking = True

    def __init__(self, fn):
        self.label = "F_" + fn.__name__
        sig = inspect.signature(fn)
        self.num_args = len(sig.parameters)
        self.fn = fn
        self.constraints = None  # Unused for now.

    def __call__(self, *args):
        """Create a DAG node that calls this function with arguments"""
        return Funcall(self, *args, blocking=self.blocking)

    def unquote(self):
        # the "machine representation" of a function is just it's name.
        return self.label

    def b_reduce(self, values):
        """Evaluate the function with arguments replaced with values"""
        if len(values) != self.num_args:
            raise Exception(
                f"Wrong number of arguments - got {len(values)}, needed {self.num_args}"
            )
        return self.fn(*values)

    def __repr__(self):
        return f"<Func {self.label}>"


# class AsyncFunc(Func):
#     blocking = False


class Foreign(Func):
    """Represents a foreign (native Python) function"""

    blocking = True

    def __init__(self, fn):
        super().__init__(fn)
        self.label = "FF_" + fn.__name__
        self.fn = self._wrapper
        self._foreign = fn

    def _wrapper(self, *args):
        return ForeignCall(self._foreign, *args)


class Handler(Func):
    """A special kind of Func that includes some infrastructure"""

    def __init__(self, fn, infrastructure):
        super().__init__(fn)
        self.infrastructure = infrastructure


# FIXME this is abstract
class Infrastructure(Quote):
    """A Quote (compile-time value) that includes some infrastructure"""

    @property
    def infrastructure(self) -> list:
        raise NotImplementedError

    def unquote(self):
        """Get the machine representation of the value"""
        return self


class If(Node):
    """Conditionals - the node evaluates to one of two branches"""

    def __init__(self, cond, then, els):
        super().__init__(cond, then, els)
        # Assign the values from self.operands so that they are the proper
        # Quoted versions. TODO fix abstractions - this is confusing
        self.cond = self.operands[0]
        self.then = self.operands[1]
        self.els = self.operands[2]

    def __repr__(self):
        return f"<If {self.cond} ? {self.then} : {self.els}>"


class Asm(Node):
    """Literal assembly instructions to execute"""

    def __init__(self, captures: list, instructions: list):
        """Run some raw assembly.

        CAPTURES specifies the objects that the assembly will operate on

        This is similar to how inline asm works in GCC - InputOperands are
        specified, and the compiler ensures they are in the right registers.

        """
        # We only init with captures so that operands (and hence descendents)
        # are only the objects that this node operates on
        super().__init__(*captures)
        self.instructions = instructions

    # TODO define __eq__, since instructions are not in operands


class Funcall(Node):
    """Call a function with some arguments

    Function can be an actual function, or a symbolic binding (allowing
    functions to be passed by reference)

    """

    def __init__(self, function, *args, blocking=True):
        if not isinstance(function, (Func, Symbol)):
            raise ValueError(f"{function} is not a Func/Symbol (it's {type(function)})")
        super().__init__(function, *args)
        self.blocking = blocking


class ForeignCall(Node):
    """Foreign function calling interface"""

    def __init__(self, fn, *args):
        super().__init__(*args)
        self.function = fn  # Must not be a Node. TODO fix - confusing
        self.args = self.operands


class Builtin(Node):
    """BuiltIn nodes are machine instructions that can be called directly"""

    def __repr__(self):
        return "$" + type(self).__name__.upper()


class Do(Node):
    """Do multiple things (PROGN)"""


## Builtins
# The __init__ forms are declared just for arity-checking.


class Eq(Builtin):
    """Check whether the top two items on the stack are equal"""

    def __init__(self, a, b):
        super().__init__(a, b)


class Atomp(Builtin):
    """Check whether something is an atom"""

    def __init__(self, a):
        super().__init__(a)


class Cons(Builtin):
    """Cons two elements together"""

    def __init__(self, a, b):
        super().__init__(a, b)


class First(Builtin):
    """CAR (first element) of a list"""

    def __init__(self, a):
        super().__init__(a)


class Rest(Builtin):
    """CDR (all elements after first) of a list"""

    def __init__(self, a):
        super().__init__(a)


class Nullp(Builtin):
    """Check whether the top item on the stack is NIL"""

    def __init__(self, a):
        super().__init__(a)


################################################################################


# Func could be made variadic by assigning self.num_args during __call__ and
# wrapping self.fn with a new function that takes a specific number of values.


# A "Type" is a function. So a string name (address) and a body. Some Types are
# builtin, which means their implementations are defined in machine.py, and they
# are skipped during the compile phase (no def/body generated for them).
#
# The compiler needs to know which machine it is targetting, so that it can skip
# generating definitions. 03/12/20


# How about... when a Node is called, it returns other Nodes. Then we'd get easy
# composition. Quote just returns itself. There are some primitive nodes, which
# return themselves, but others could return more nodes?! So in compiling, every
# non-primitive node calls itself and compiles the results.
#
# No. That's reimplementing what already exists - abstraction through defun.
# Cond can easily be defun'd, using the If primitive.


### TODO These should really be in stdlib:


@Func
def Nth(n, lst):
    # NOTE it's *wrong* to use an FCALL in a built-in language function... but
    # this is MVP :)
    return If(Eq(n, 0), First(lst), Nth(ForeignCall(lambda x: x - 1, x), Rest(lst)))


@Func
def Second(lst):
    return Nth(1, lst)


@Func
def Third(lst):
    return Nth(2, lst)


@Func
def Fourth(lst):
    return Nth(3, lst)


# Aliases
Car = First
Cdr = Rest
Cadr = Second
Caddr = Third
Cadddr = Fourth
