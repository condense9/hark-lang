# import c9.lang as l
import sys

import itertools
import lark
from lark import Transformer, v_args

import c9.compiler as compiler
import c9.lang as l
import c9.machine.types as mt
import c9.machine.instructionset as mi
import c9.controllers.local as local

EXPR_TESTS = [
    # --
    "1",
    "2.0",
    '"foo"',
    "true",
    "false",
    "nil",
    "symb",
    "'symb",
    "(g a)",
    "'(g a)",
    '{1 2 3 "b"}',
    # -- specials
    "(if a 1 2)",
    "(if (f x) 1 (do 1 2))",
    "(def f (x y) (print x) x)",
    "(let ((x 1) (y 2)) x)",
]


# Node : Branch | Terminal
#
# Branch : Funcall Node*
#        | ForeignCall Node*
#        | If cond then else
#        | Do Node*
#        | Asm (?)
#
# Terminal: Literal | Symbol


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


@v_args(inline=True)
class TopT(Transformer):
    def __init__(self):
        self.defs = {}
        super().__init__()

    def number(self, value):
        return mt.C9Number(eval(value))

    def string(self, value):
        return mt.C9String(eval(value))

    def true(self, value):
        return True

    def false(self, value):
        return False

    def nil(self, value):
        return None

    def list_(self, function, *args):
        # C9List??
        if function == "print":
            assert len(args) == 1
            return l.Asm(args, [mi.Print()])
        else:
            return l.Funcall(function, *args)

    def map_(self, *items):
        return dict(grouper(items, 2))

    def symbol(self, name):
        return mt.C9Symbol(str(name))

    def quote(self, value):
        return l.Quote(value)

    def if_(self, cond, then, els):
        return l.If(cond, then, els)

    def do(self, *things):
        return l.Do(things)

    def def_params(self, *params):
        assert all(isinstance(name, mt.C9Symbol) for name in params)
        return [param for param in params]

    # def def_body(self, *items):
    #     return list(items)

    def def_(self, name, bindings, body):
        assert isinstance(name, mt.C9Symbol)
        assert isinstance(bindings, list)
        self.defs[name] = (bindings, body)
        return None


def main(make_tree=False):
    # https://github.com/lark-parser/lark/blob/master/examples/python_parser.py

    start = "file"
    parser = lark.Lark.open("c9_lisp.lark", parser="lalr", start=start)

    for i, t in enumerate(EXPR_TESTS[:14]):
        print(f"------------------------------------------------------[{start}_{i}]-")
        print("\n".join(f"{i+1} | {l}" for i, l in enumerate(t.split("\n"))))
        print("  :")
        tree = parser.parse(t)
        if make_tree:
            lark.tree.pydot__tree_to_png(tree, f"tree_{start}_{i}.png")
        print(tree.pretty())

        top = TopT()
        new_tree = top.transform(tree)
        print(new_tree)
        print(top.defs)


def test():
    parser = lark.Lark.open("c9_lisp.lark", parser="lalr")

    with open(sys.argv[1]) as f:
        tree = parser.parse(f.read())

    print(tree.pretty())

    top = TopT()
    top.transform(tree)
    # print(top.defs)

    main_compiled = compiler.compile_function(*top.defs["main"])
    # main_compiled.listing()

    defs = {"main": main_compiled.code}

    exe = compiler.link(defs, "main", entrypoint_fn="main")

    print(exe.listing())
    # compiled = {name: compiler.compile_function(f) for name, f in top.defs}

    try:
        controller = local.run_exe(exe, sys.argv[2:], do_probe=True)
    finally:
        # for p in controller.probes:
        #     print("\n".join(p.logs))
        #     print("")
        # print("-- END LOGS")
        pass


if __name__ == "__main__":
    test()
