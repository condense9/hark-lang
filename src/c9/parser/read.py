"""Read an AST"""

import c9.machine.types as mt
from lark import Token, Transformer, Tree, v_args


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

    def number(self, value):
        return mt.C9Number(eval(value))

    def string(self, value):
        return mt.C9String(eval(value))

    def true(self, value):
        return mt.C9True()

    def nil(self, value):
        return mt.C9Null()

    # def map_(self, *items):
    #     return mt.C9Dict(grouper(items, 2))

    def m_quote(self, *sexp):
        return Tree("quote", sexp)
