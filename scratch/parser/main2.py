import c9.lang as l
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
    "f a",
    "(f) a",
    "(f a)",
    "f a b c",
    "((f a) b)",
]


class C9Indenter(Indenter):
    NL_type = "_NEWLINE"
    # OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
    # CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


def main(make_tree=False):
    # https://github.com/lark-parser/lark/blob/master/examples/python_parser.py
    parser = lark.Lark.open("c9_func.lark", parser="lalr", postlex=C9Indenter())

    for i, t in enumerate(TESTS):
        print(f"-[{i}]------------------------------------------------------")
        print(t)
        print(":")
        tree = parser.parse(t)
        if make_tree:
            lark.tree.pydot__tree_to_png(tree, f"tree{i}.png")
        print(tree.pretty())


if __name__ == "__main__":
    main()
