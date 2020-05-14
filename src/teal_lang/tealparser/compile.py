import itertools
from functools import singledispatch, singledispatchmethod

from ..machine import instructionset as mi
from ..machine import types as mt
from . import parser as p

import logging

LOG = logging.getLogger(__name__)


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


@singledispatch
def teal_compile(node) -> list:
    raise NotImplementedError(n)


@teal_compile.register
def _(n: p.N_Literal):
    val = mt.to_teal_type(n.value)
    return [mi.PushV(val)]


@teal_compile.register
def _(n: p.N_Id):
    return [mi.PushB(mt.TlSymbol(n.name))]


@teal_compile.register
def _(n: p.N_Progn):
    # only keep the last result
    discarded = flatten(teal_compile(exp) + [mi.Pop()] for exp in n.exprs[:-1])
    return discarded + teal_compile(n.exprs[-1])


@teal_compile.register
def _(n: p.N_Call):
    arg_code = flatten(teal_compile(arg) for arg in n.args)
    return arg_code + teal_compile(n.fn) + [mi.Call(mt.TlInt(len(n.args)))]


@teal_compile.register
def _(n: p.N_Async):
    if not isinstance(n.call, p.N_Call):
        raise ValueError(f"Can't use async with {n.call}")
    call = teal_compile(n.call)
    # swap the normal call for an ACall
    return call[:-1] + [mi.ACall(mt.TlInt(len(n.call.args)))]


@teal_compile.register
def _(n: p.N_Await):
    call = teal_compile(n.call)
    # swap the normal call for an ACall
    return call[:-1] + [mi.ACall(mt.TlInt(len(n.call.args)))]


@teal_compile.register
def _(n: p.N_If):
    cond_code = teal_compile(n.cond)
    else_code = teal_compile(n.els)
    then_code = teal_compile(n.then)
    return [
        # --
        *cond_code,
        mi.PushV(mt.TlTrue()),
        mi.JumpIE(mt.TlInt(len(else_code) + 1)),  # to then_code
        *else_code,
        mi.Jump(mt.TlInt(len(then_code))),  # to Return
        *then_code,
    ]


@teal_compile.register
def _(n: p.N_Binop):
    rhs = teal_compile(n.rhs)

    if n.op == "=":
        if not isinstance(n.lhs, N_Id):
            raise ValueError(f"Can't assign to non-identifier {n.lhs}")
        return rhs + [mi.Bind(mt.TlSymbol(str(n.lhs.name)))]

    else:
        lhs = teal_compile(n.lhs)
        # TODO check arg order. Reverse?
        return rhs + lhs + [mi.PushB(mt.TlSymbol(str(n.op))), mi.Call(mt.TlInt(2))]


@teal_compile.register
def _(n: p.N_Definition):
    bindings = [mi.Bind(mt.TlSymbol(str(name))) for name in reversed(n.paramlist)]
    body = teal_compile(n.body)
    return bindings + body + [mi.Return()]


# Top levels

# All of the (stateless) things above could be moved into the class below to
# give them state, and, for example, do things like name-check, or extend the
# infix operator table haskell-style.


class CompileToplevel:
    def __init__(self, exprs):
        self.definitions = {}
        for e in exprs:
            self.compile_toplevel(e)

    @singledispatchmethod
    def compile_toplevel(self, n):
        raise NotImplementedError(n)

    @compile_toplevel.register
    def _(self, n: p.N_Definition):
        self.definitions[n.name] = mt.TlFunction(teal_compile(n))

    @compile_toplevel.register
    def _(self, n: p.N_Import):
        # TODO __builtins__?
        name = n.as_ or n.name
        self.definitions[name] = mt.TlForeign([n.name, n.mod])


# FIXME: need a way to refer to a function directly

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], "r") as f:
        text = f.read()

    res = CompileToplevel(p.parse(text, debug_lex=False))
    print(res.definitions)
