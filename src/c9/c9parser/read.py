"""Read an AST"""

from lark import Token, Transformer, Tree, v_args

from ..machine import types as mt
from .load import exp_parser


@v_args(inline=True)
class ReadSexp(Transformer):
    def list_(self, *values):
        return mt.C9List(values)

    def symbol(self, value):
        return mt.C9Symbol(str(value))

    def literal(self, value):
        return value


@v_args(inline=True)
class ReadLiterals(Transformer):
    """Read literals in the tree"""

    def float_(self, value):
        return mt.C9Float(eval(value))

    def int_(self, value):
        return mt.C9Int(eval(value))

    def string_(self, value):
        return mt.C9String(eval(value))

    def true_(self, value):
        return mt.C9True()

    def nil(self, value):
        return mt.C9Null()

    # def map_(self, *items):
    #     return mt.C9Dict(grouper(items, 2))

    def m_quote(self, *sexp):
        return Tree("quote", sexp)

    def m_async(self, sexp):
        return Tree("async_", sexp.children)

    def m_wait(self, sexp):
        wait = Tree("symbol", [Token("IDENTIFIER", "wait")])
        return Tree("list_", [wait, sexp])


def read_exp(exp):
    """Read a single literal expression"""
    parser = exp_parser()
    tree = parser.parse(exp)
    return ReadLiterals().transform(tree).children[0]
