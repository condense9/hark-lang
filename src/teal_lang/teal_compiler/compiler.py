"""Optimise and compile an AST into executable code"""
import itertools
import logging
from functools import singledispatch, singledispatchmethod, wraps
from typing import Dict, Tuple

from ..machine import instructionset as mi
from ..machine import types as mt
from ..machine.executable import Executable
from ..teal_parser import nodes
from .attributes import parse_attribute

LOG = logging.getLogger(__name__)


# A label to point at the beginning on the function, prefixed with "!" to imply
# that it is automatically created:
START_LABEL = "!start"


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


class CompileError(Exception):
    pass


def optimise_block(n: nodes.N_Definition, block: nodes.N_Progn):
    """Optimise a single block (progn) of expressions"""
    if not isinstance(block, nodes.N_Progn):
        raise ValueError

    last = block.exprs[-1]

    if isinstance(last, nodes.N_Call) and last.fn.name == n.name:
        # recursive call, optimise it! Replace the N_Call with direct evaluation
        # of the arguments and a jump back to the start
        new_last_items = list(last.args) + [nodes.N_Goto(None, START_LABEL)]
        return_values = nodes.N_MultipleValues(None, new_last_items)
        return nodes.N_Progn(None, block.exprs[:-1] + [return_values])

    elif isinstance(last, nodes.N_If):
        new_cond = nodes.N_If(
            None, last.cond, optimise_block(n, last.then), optimise_block(n, last.els)
        )
        return nodes.N_Progn(None, block.exprs[:-1] + [new_cond])

    else:
        # Nothing to optimise
        return block


def optimise_tailcall(n: nodes.N_Definition):
    """Optimise tail calls in a definition"""
    n.body = optimise_block(n, n.body)
    return n


def replace_gotos(code: list):
    """Replace Labels and Gotos with Jumps"""
    labels = {}
    original_positions = []
    for idx, instr in enumerate(code):
        if isinstance(instr, nodes.N_Label):
            offset = idx - len(labels)
            labels[instr.name] = offset
            original_positions.append(idx)

    for idx in original_positions:
        code.pop(idx)

    for idx, instr in enumerate(code):
        if isinstance(instr, nodes.N_Goto):
            # + 1 to compensate for the fact that the IP is advanced before
            # the current instruction is evaluated.
            offset = labels[instr.name] - (idx + 1)
            code[idx] = mi.Jump(mt.TlInt(offset))

    return code


class CompileToplevel:
    def __init__(self, exprs):
        """Compile a toplevel list of expressions"""
        self.functions = {}
        self.attributes = {}
        self.bindings = {}
        self.labels = {}
        self.instruction_idx = 0
        for e in exprs:
            self.compile_toplevel(e)

    def make_function(self, n: nodes.N_Definition, name="lambda") -> str:
        """Make a new executable function object with a unique name, and save it"""
        count = len(self.functions)
        identifier = f"#{count}:{name}"
        start_label = nodes.N_Label(None, START_LABEL)
        code = self.compile_function(optimise_tailcall(n))
        fn_code = replace_gotos([start_label] + code)
        self.functions[identifier] = fn_code
        # self.attributes[identifier] = parse_attribute(n.attribute)
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
    def _(self, n: nodes.N_Goto):
        # Will be replaced later
        return [n]

    @compile_expr.register
    def _(self, n: nodes.N_Label):
        raise NotImplementedError

    @compile_expr.register
    def _(self, n: nodes.N_Lambda):
        # Create a local binding to the function
        identifier = self.make_function(n)
        stack = None
        # TODO?! closures! Need a mi.MakeClosure instruction that updates the
        # top value (TlFunctionPtr) on the stack to reference the current
        # activation record. The Call logic would be different too.
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
    def _(self, n: nodes.N_MultipleValues):
        # like progn, but keep everything
        return flatten(self.compile_expr(exp) for exp in n.exprs)

    def _compile_call(self, n: nodes.N_Call, is_async: bool):
        # NOTE: parser only allows direct, named function calls atm, not
        # arbitrary expressions, so no need to check the type of n.fn
        arg_code = flatten(self.compile_expr(arg) for arg in n.args)
        instr = mi.ACall if is_async else mi.Call
        return (
            arg_code
            + self.compile_expr(n.fn)
            + [instr(mt.TlInt(len(n.args)), source=n.index)]
        )

    @compile_expr.register
    def _(self, n: nodes.N_Call):
        return self._compile_call(n, False)

    @compile_expr.register
    def _(self, n: nodes.N_Async):
        if not isinstance(n.expr, nodes.N_Call):
            raise ValueError(f"Can't use async with {n.expr}")
        return self._compile_call(n.expr, True)

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
            mi.JumpIf(mt.TlInt(len(else_code) + 1)),  # to then_code
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


def tl_compile(top_nodes: list) -> Executable:
    """Compile top-level nodes into an executable"""
    collection = CompileToplevel(top_nodes)

    location_offset = 0
    code = []
    locations = {}
    for fn_name, fn_code in collection.functions.items():
        locations[fn_name] = location_offset
        location_offset += len(fn_code)
        code += fn_code

    return Executable(collection.bindings, locations, code, collection.attributes)
