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
    "(g, a)",
    "g a",
    "g (a, b, c)",
    # -- lists
    "lambda x b: 1",
    """lambda x:
    1
    """,
    "lambda foo: print foo; foo",
    # -- cond
    "if a: 1 else: 2",
]

BODY_TESTS = [
    """
def f:
    if a:
        print bla
        print bla; print bla
        bla
    else: 2
""",
    # -- bindings
    """def f x: let a = 1 in a + x""",
    """
def f:
    let a = 1
        b = 2
    in a
    """,
    # -- func
    "def f x: 1 + f (x - 1) * 3",
]


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


def test(tests, start, make_tree):
    parser = lark.Lark.open(
        "c9_func.lark", parser="lalr", start=start, postlex=C9Indenter()
    )
    for i, t in enumerate(tests):
        print(f"------------------------------------------------------[{start}_{i}]-")
        print("\n".join(f"{i+1} | {l}" for i, l in enumerate(t.split("\n"))))
        print("  :")
        tree = parser.parse(t)
        if make_tree:
            lark.tree.pydot__tree_to_png(tree, f"tree_{start}_{i}.png")
        print(tree.pretty())


def main(make_tree=False):
    # https://github.com/lark-parser/lark/blob/master/examples/python_parser.py

    body_tests = [t.strip() + "\n" for t in BODY_TESTS]

    test(EXPR_TESTS, "exp", make_tree)
    test(body_tests, "body", make_tree)


if __name__ == "__main__":
    main()
