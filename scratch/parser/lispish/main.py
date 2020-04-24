# import c9.lang as l
import sys

import itertools
import lark
from lark import Transformer, v_args, Tree, Token

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
    "'(g a)",
    "(g a)",
    # '{1 2 3 "b"}',
    # -- specials
    "(if a 1 2)",
    "(if (f x) 1 (do 1 2))",
    "(let ((x 1) (y 2)) x)",
]

FILE_TESTS = [
    "(def f (x y) (print x) x)",
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


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


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
    """Read the tree"""

    def number(self, value):
        return mt.C9Number(eval(value))

    def string(self, value):
        return mt.C9String(eval(value))

    def true(self, value):
        return mt.C9True()

    def false(self, value):
        return mt.C9False()

    def nil(self, value):
        return mt.C9Null()


class Evaluate:
    def __init__(self, tree):
        self.defs = {}
        print("eval", tree)
        self.code = getattr(self, tree.data)(*tree.children)

    def quote(self, value):
        result = ReadSexp().transform(value)
        return [mi.PushV(result)]

    def m_quote(self, value):
        result = ReadSexp().transform(value)
        return [mi.PushV(result)]

    def atom(self, value):
        return Evaluate(value).code

    def literal(self, value):
        return [mi.PushV(value)]

    def symbol(self, value):
        return [mi.PushB(mt.C9Symbol(value))]

    def list_(self, function, *args):
        builtins = {
            # --
            "print": mi.Print,
            "eq": mi.Eq,
            "atomp": mi.Atomp,
            "nullp": mi.Nullp,
            "list": mi.List,
            "first": mi.First,
            "rest": mi.Rest,
            "wait": mi.Wait,
            "+": mi.Plus,
            "*": mi.Plus,
            "nth": mi.Nth,
        }
        arg_code = flatten(Evaluate(arg).code for arg in args)

        if isinstance(function, mt.C9Symbol) and function in builtins:
            call = builtins[function](len(args))
        else:
            call = mi.Call(len(args))

        function_code = Evaluate(function).code
        return [*arg_code, *function_code, call]

    def if_(self, cond, then, els):
        cond_code = Evaluate(cond).code
        else_code = Evaluate(els).code
        then_code = Evaluate(then).code
        return [
            # --
            *cond_code,
            mi.PushV(mt.C9True()),
            mi.JumpIE(len(else_code)),
            *else_code,
            mi.Jump(len(then_code)),  # to Return
            *then_code,
        ]

    def do_block(self, *things):
        return flatten(Evaluate(thing).code for thing in things)

    def let(self, bindings, body):
        code = []
        for b in bindings.children:
            name, value = b.children[:]
            assert isinstance(name, Token)
            code += Evaluate(value).code + [mi.Bind(str(name))]
        code += Evaluate(body).code
        return code


class CompileFile:
    def __init__(self, tree):
        self.defs = {}
        self.code = getattr(self, tree.data)(*tree.children)

    def def_(self, name, bindings, body):
        assert isinstance(name, mt.C9Symbol)
        assert all(isinstance(name, mt.C9Symbol) for name in bindings)
        self.defs[name] = (bindings, Evaluate(body))


def main(make_tree=False):
    # https://github.com/lark-parser/lark/blob/master/examples/python_parser.py

    start = "sexp"  # skip file
    parser = lark.Lark.open("c9_lisp.lark", parser="lalr", start=start)

    for i, t in enumerate(EXPR_TESTS[:14]):
        print(f"------------------------------------------------------[{start}_{i}]-")
        print("\n".join(f"{i+1} | {l}" for i, l in enumerate(t.split("\n"))))
        print("  :")
        tree = parser.parse(t)
        if make_tree:
            lark.tree.pydot__tree_to_png(tree, f"tree_{start}_{i}.png")
        print(tree.pretty())

        reader = ReadLiterals()
        tree = reader.transform(tree)
        evaluated = Evaluate(tree)
        print("evaluated:", tree)
        print(evaluated.code)


def test():
    parser = lark.Lark.open("c9_lisp.lark", parser="lalr")

    with open(sys.argv[1]) as f:
        tree = parser.parse(f.read())

    print(tree.pretty())

    top = CompileT()
    top.transform(tree)
    # print(top.defs)

    main_compiled = CompileFile(tree.children[0])
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
        print(controller.outputs[0])


if __name__ == "__main__":
    # test()
    main()
