"""Evaluate an AST"""

import logging
import itertools
import c9.machine.instructionset as mi
import c9.machine.types as mt
from lark import Token
from .read import ReadSexp, ReadLiterals
from .load import exp_parser, file_parser

LOG = logging.getLogger(__name__)


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


class Evaluate:
    def __init__(self, tree):
        # print("eval", tree)
        self.code = getattr(self, tree.data)(*tree.children)

    def quote(self, value):
        result = ReadSexp().transform(value)
        return [mi.PushV(mt.C9Quote(result))]

    def atom(self, value):
        return Evaluate(value).code

    def literal(self, value):
        return [mi.PushV(value)]

    def symbol(self, value):
        return [mi.PushB(mt.C9Symbol(str(value)))]

    def list_(self, function, *args):
        # a normal call
        arg_code = flatten(Evaluate(arg).code for arg in args)
        return arg_code + Evaluate(function).code + [mi.Call(len(args))]

    def async_(self, function, *args):
        # an async call
        # FIXME - not sure what happens if this is nested.
        arg_code = flatten(Evaluate(arg).code for arg in args)
        return arg_code + Evaluate(function).code + [mi.ACall(len(args))]

    def if_(self, cond, then, els):
        cond_code = Evaluate(cond).code
        else_code = Evaluate(els).code
        then_code = Evaluate(then).code
        return [
            # --
            *cond_code,
            mi.PushV(mt.C9True()),
            mi.JumpIE(len(else_code) + 1),  # to then_code
            *else_code,
            mi.Jump(len(then_code)),  # to Return
            *then_code,
        ]

    def do_block(self, *stmts):
        # in a do block, only the last result is retained. Every previous
        # statement is executed and then discarded (popped)
        discarded = flatten(Evaluate(stmt).code + [mi.Pop()] for stmt in stmts[:-1])
        return discarded + Evaluate(stmts[-1]).code

    def let(self, bindings, body):
        code = []
        for b in bindings.children:
            name, value = b.children[:]
            assert isinstance(name, Token)
            code += Evaluate(value).code + [mi.Bind(str(name))]
        code += Evaluate(body).code
        return code


class EvaluateToplevel:
    """Evaluate the top-level and collect definitions"""

    def __init__(self, tree):
        self.defs = {}
        self.foreigns = {}
        assert tree.data == "file"
        for c in tree.children:
            getattr(self, c.data)(*c.children)

    def python(self, fn_name, mod_name, import_as=None):
        dest_name = import_as if import_as else fn_name
        self.foreigns[str(dest_name)] = (str(fn_name), str(mod_name))

    def def_(self, name, bindings, body):
        assert isinstance(name, Token)
        # NOTE - arg stack is in reverse order, so the bindings are reversed
        bindings_code = [mi.Bind(str(b)) for b in reversed(bindings.children)]
        self.defs[str(name)] = bindings_code + Evaluate(body).code + [mi.Return()]


## User interface:


def evaluate_exp(exp: str):
    parser = exp_parser()
    tree = parser.parse(exp)
    ast = ReadLiterals().transform(tree)
    return Evaluate(ast)


def evaluate_toplevel(content: str):
    parser = file_parser()
    tree = parser.parse(content)
    ast = ReadLiterals().transform(tree)
    LOG.debug(ast.pretty())
    return EvaluateToplevel(ast)
