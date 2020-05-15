import itertools
from functools import singledispatch, singledispatchmethod

from ..machine import instructionset as mi
from ..machine import types as mt
from . import parser as p
from ..machine.executable import link

import logging

LOG = logging.getLogger(__name__)


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


class CompileToplevel:
    def __init__(self, exprs):
        """Compile a toplevel list of expressions"""
        self.functions = {}
        self.global_bindings = {}
        for e in exprs:
            self.compile_toplevel(e)

    def make_function(self, n: p.N_Definition) -> str:
        """Make a new executable function object with a unique name, and save it"""
        count = len(self.functions)
        identifier = f"#{count}:{n.name}"
        fn_code = self.compile_function(n)
        self.functions[identifier] = fn_code
        return identifier

    def compile_function(self, n) -> list:
        """Compile a function into executable code"""
        bindings = [mi.Bind(mt.TlSymbol(arg)) for arg in reversed(n.paramlist)]
        body = self.compile_expr(n.body)
        return bindings + body + [mi.Return()]

    # At the toplevel, no executable code is created - only global_bindings

    @singledispatchmethod
    def compile_toplevel(self, n) -> None:
        raise NotImplementedError(n)

    @compile_toplevel.register
    def _(self, n: p.N_Definition):
        # Add to the global global_bindings table
        identifier = self.make_function(n)
        self.global_bindings[n.name] = mt.TlFunctionPtr(identifier, None)

    @compile_toplevel.register
    def _(self, n: p.N_Import):
        # TODO __builtins__?
        name = n.as_ or n.name
        self.global_bindings[name] = mt.TlForeignPtr(n.name, n.mod)

    # Expressions result in executable code being created

    @singledispatchmethod
    def compile_expr(self, node) -> list:
        raise NotImplementedError(n)

    @compile_expr.register
    def _(self, n: p.N_Definition):
        # Create a local binding to the function
        identifier = self.make_function(n)
        stack = None  # TODO?!
        return [
            mi.PushV(mt.TlFunctionPtr(identifier, stack)),
            mi.Bind(mt.TlSymbol(n.name)),
            mi.PushB(mt.TlSymbol(n.name)),  # 'return' the func ptr
        ]

    @compile_expr.register
    def _(self, n: p.N_Literal):
        val = mt.to_teal_type(n.value)
        return [mi.PushV(val)]

    @compile_expr.register
    def _(self, n: p.N_Id):
        return [mi.PushB(mt.TlSymbol(n.name))]

    @compile_expr.register
    def _(self, n: p.N_Progn):
        # only keep the last result
        discarded = flatten(self.compile_expr(exp) + [mi.Pop()] for exp in n.exprs[:-1])
        return discarded + self.compile_expr(n.exprs[-1])

    @compile_expr.register
    def _(self, n: p.N_Call):
        arg_code = flatten(self.compile_expr(arg) for arg in n.args)
        return arg_code + self.compile_expr(n.fn) + [mi.Call(mt.TlInt(len(n.args)))]

    @compile_expr.register
    def _(self, n: p.N_Async):
        if not isinstance(n.call, p.N_Call):
            raise ValueError(f"Can't use async with {n.call}")
        call = self.compile_expr(n.call)
        # swap the normal call for an ACall
        return call[:-1] + [mi.ACall(mt.TlInt(len(n.call.args)))]

    @compile_expr.register
    def _(self, n: p.N_Await):
        call = self.compile_expr(n.call)
        # swap the normal call for an ACall
        return call[:-1] + [mi.ACall(mt.TlInt(len(n.call.args)))]

    @compile_expr.register
    def _(self, n: p.N_If):
        cond_code = self.compile_expr(n.cond)
        else_code = self.compile_expr(n.els)
        then_code = self.compile_expr(n.then)
        return [
            # --
            *cond_code,
            mi.PushV(mt.TlTrue()),
            mi.JumpIE(mt.TlInt(len(else_code) + 1)),  # to then_code
            *else_code,
            mi.Jump(mt.TlInt(len(then_code))),  # to Return
            *then_code,
        ]

    @compile_expr.register
    def _(self, n: p.N_Binop):
        rhs = self.compile_expr(n.rhs)

        if n.op == "=":
            if not isinstance(n.lhs, N_Id):
                raise ValueError(f"Can't assign to non-identifier {n.lhs}")
            return rhs + [mi.Bind(mt.TlSymbol(str(n.lhs.name)))]

        else:
            lhs = self.compile_expr(n.lhs)
            # TODO check arg order. Reverse?
            return rhs + lhs + [mi.PushB(mt.TlSymbol(str(n.op))), mi.Call(mt.TlInt(2))]


# FIXME: need a way to refer to a function directly

if __name__ == "__main__":
    import sys
    import pprint

    with open(sys.argv[1], "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"

    res = CompileToplevel(p.parse(text, debug_lex=debug))

    pprint.pprint(res.global_bindings)
    print("")
    pprint.pprint(res.functions)

    print(link(res.global_bindings, res.functions).listing())
