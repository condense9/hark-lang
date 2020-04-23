# import c9.lang as l
import sys
import lark
from lark.indenter import Indenter

# Node : Branch | Terminal
#
# Branch : Funcall Node*
#        | ForeignCall Node*
#        | If cond then else
#        | Do Node*
#        | Asm (?)
#
# Terminal: Literal | Symbol

TESTS = [
    # --
    "service foo",
    # --
    "x = 1",
    # --
    """
x = 1
b = \"bla\"""",
    # --
    "f m c x = (m * x) + c",
    # --
    "f x = (g x) + 1",
    # --
    "a = f x y",
    # --
    "f a = h a 2 \nf a = ((h a) 2)",
    # --
    "f = null",
    # --
    "f x = 1 + f x * 3",
]

EXPR_TESTS = [
    # --
    "1",
    '"foo"',
    "symb",
    "(f, a)",
    "f a",
    "f(a, b, c)",
    # -- lists
    "lambda x b: 1",
    """lambda x:
    1
    """,
    "lambda foo: print foo; foo",
    # -- cond
    "if a: 1 else: 2",
    """if a:
    print bla
    print bla; print bla
    bla
else: 2""",
    # -- bindings
    """let a = 1 in: a""",
    """let a = 1
    b = 2
in: a""",
]

# foo = """
# foo x, y:
#     let a = b, bla = bla:
#         x + a
# """

# CLOSURE = """
# make_counter = let val = 0: lambda: val = val + 1; val
# """

# The language is imperative in some places, and not in others. "Do" block


class C9Indenter(Indenter):
    NL_type = "_NEWLINE"
    OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
    CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4  # replaces tabs with this many spaces


def main(make_tree=False):
    # https://github.com/lark-parser/lark/blob/master/examples/python_parser.py
    parser = lark.Lark.open("c9_func.lark", parser="lalr", postlex=C9Indenter())

    for i, t in enumerate(EXPR_TESTS):
        print(f"-[{i}]------------------------------------------------------")
        print(t)
        print(":")
        tree = parser.parse(t)
        if make_tree:
            lark.tree.pydot__tree_to_png(tree, f"tree{i}.png")
        print(tree.pretty())


if __name__ == "__main__":
    main()
