# https://github.com/lark-parser/lark/blob/master/docs/json_tutorial.md
# https://lark-parser.readthedocs.io/en/latest/lark_cheatsheet.pdf
import sys
import lark

with open("c9_func.lark", "r") as f:
    parser = lark.Lark(f.read(), parser="lalr")


tests = [
    # --
    "foobar",
    # Values
    ":cow",
    "true",
    '"foo"',
    # Function call
    'print "hello" 1',
    'print("hello", "world", 1)',
    # foreign
    """
a = Python("module", "fn_a", 1)
main x = a(x) + 1
    """,
]


def make_png(tree, filename):
    lark.tree.pydot__tree_to_png(tree, filename)


for i, t in enumerate(tests_v2):
    print(
        "--------------------------------------------------------------------------------"
    )
    print(t)
    print(":")
    tree = parser.parse(t)
    make_png(tree, f"tree{i}.png")
    print(tree.pretty())


# The language is a list of expressions, but the compiler requires that list to
# only contain function definitions.
#
# Compilation: for each item (function definition), compile it
