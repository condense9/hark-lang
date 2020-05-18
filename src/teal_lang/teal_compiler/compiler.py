import itertools
import logging
from functools import singledispatch, singledispatchmethod
from typing import Dict, Tuple

from ..machine import instructionset as mi
from ..machine import types as mt
from ..teal_parser import nodes

LOG = logging.getLogger(__name__)


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


class CompileError(Exception):
    pass


class CompileToplevel:
    def __init__(self, exprs):
        """Compile a toplevel list of expressions"""
        self.functions = {}
        self.bindings = {}
        for e in exprs:
            self.compile_toplevel(e)

    def make_function(self, n: nodes.N_Definition, name="lambda") -> str:
        """Make a new executable function object with a unique name, and save it"""
        count = len(self.functions)
        identifier = f"#{count}:{name}"
        fn_code = self.compile_function(n)
        self.functions[identifier] = fn_code
        return identifier

    def compile_function(self, n: nodes.N_Definition) -> list:
        """Compile a function into executable code"""
        bindings = flatten(
            [[mi.Bind(mt.TlSymbol(arg)), mi.Pop()] for arg in reversed(n.paramlist)]
        )
        body = self.compile_expr(n.body)
        return bindings + body + [mi.Return()]

    ## At the toplevel, no executable code is created - only bindings

    @singledispatchmethod
    def compile_toplevel(self, n) -> None:
        raise CompileError(f"{n}: Invalid at top level")

    @compile_toplevel.register
    def _(self, n: nodes.N_Call):
        if not isinstance(n.fn, nodes.N_Id) or n.fn.name != "import":
            raise CompileError(f"{n}: Only `import' can be called at top level")

        if len(n.args) not in (2, 3):
            raise CompileError(f"{n}: usage: import(name, source, [qualifier])")

        if not isinstance(n.args[0].value, nodes.N_Id):
            raise CompileError(f"{n}: Import name must be an identifier")

        if not isinstance(n.args[1].value, nodes.N_Id):
            raise CompileError(f"{n}: Import source must be an identifier")

        import_symb = n.args[0].value.name
        from_kw = n.args[1].symbol
        from_val = n.args[1].value.name

        if from_kw and from_kw.name != ":python":
            raise CompileError(f"{n}: Can't import non-python")

        if len(n.args) == 3:
            # TODO? check n.args[2].symbol == ":as"
            if not isinstance(n.args[2].value, nodes.N_Id):
                raise CompileError(f"{n}: Import qualifier must be an identifier")

            as_val = n.args[2].value.name
        else:
            as_val = import_symb

        self.bindings[as_val] = mt.TlForeignPtr(import_symb, from_val)

    @compile_toplevel.register
    def _(self, n: nodes.N_Definition):
        identifier = self.make_function(n, n.name)
        self.bindings[n.name] = mt.TlFunctionPtr(identifier, None)

    ## Expressions result in executable code being created

    @singledispatchmethod
    def compile_expr(self, node) -> list:
        raise NotImplementedError(node)

    @compile_expr.register
    def _(self, n: nodes.N_Lambda):
        # Create a local binding to the function
        identifier = self.make_function(n)
        stack = None  # TODO?! closures!
        return [mi.PushV(mt.TlFunctionPtr(identifier, stack))]

    @compile_expr.register
    def _(self, n: nodes.N_Literal):
        val = mt.to_teal_type(n.value)
        return [mi.PushV(val)]

    @compile_expr.register
    def _(self, n: nodes.N_Id):
        return [mi.PushB(mt.TlSymbol(n.name))]

    @compile_expr.register
    def _(self, n: nodes.N_Progn):
        # only keep the last result
        discarded = flatten(self.compile_expr(exp) + [mi.Pop()] for exp in n.exprs[:-1])
        return discarded + self.compile_expr(n.exprs[-1])

    @compile_expr.register
    def _(self, n: nodes.N_Call):
        arg_code = flatten(self.compile_expr(arg) for arg in n.args)
        call_inst = mi.ACall if isinstance(n.fn, nodes.N_Async) else mi.Call
        return arg_code + self.compile_expr(n.fn) + [call_inst(mt.TlInt(len(n.args)))]

    @compile_expr.register
    def _(self, n: nodes.N_Async):
        if not isinstance(n.expr, nodes.N_Id):
            raise ValueError(f"Can't use async with {n.expr}")
        return self.compile_expr(n.expr)

    @compile_expr.register
    def _(self, n: nodes.N_Argument):
        # TODO optional arguments...
        return self.compile_expr(n.value)

    @compile_expr.register
    def _(self, n: nodes.N_Await):
        if not isinstance(n.expr, (nodes.N_Call, nodes.N_Id)):
            raise ValueError(f"Can't use await with {n.expr} - {type(n.expr)}")
        val = self.compile_expr(n.expr)
        return val + [mi.Wait(mt.TlInt(0))]

    @compile_expr.register
    def _(self, n: nodes.N_If):
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
    def _(self, n: nodes.N_Binop):
        rhs = self.compile_expr(n.rhs)

        if n.op == "=":
            if not isinstance(n.lhs, nodes.N_Id):
                raise ValueError(f"Can't assign to non-identifier {n.lhs}")
            return rhs + [mi.Bind(mt.TlSymbol(str(n.lhs.name)))]

        else:
            lhs = self.compile_expr(n.lhs)
            # TODO check arg order. Reverse?
            return rhs + lhs + [mi.PushB(mt.TlSymbol(str(n.op))), mi.Call(mt.TlInt(2))]


###


def tl_compile(top_exprs: list) -> Tuple[Dict, Dict]:
    """Compile top-level expressions and return (bindings, functions)"""
    res = CompileToplevel(top_exprs)
    return res.bindings, res.functions
