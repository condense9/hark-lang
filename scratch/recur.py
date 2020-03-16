import random
import time

import dataclasses as dc
import dis


def disassemble(fn):
    # dis.dis(fn)
    for instr in dis.get_instructions(fn):
        print(instr.opname, instr.argrepr)
    return fn


class Future:
    _count = 0

    def __init__(self, name=None):
        if name:
            self.name = name
        else:
            self._count += 1
            self.name = f"#F{self._count}"

    def add_handler(self, handler):
        # handler: callable
        self._handlers.append(handler)

    def resolve(self, value):
        # The implementation can wrap fn in whatever it wants to enable
        # concurrency, race condition resolution, etc
        for fn in self._handlers:
            fn(value)


class Callable:
    """A callable object must implement 'call'"""

    _count = 0

    def __init__(self, name=None):
        if name:
            self.name = name
        else:
            self._count += 1
            self.name = f"#C{self._count}"

    # must def call

    def __repr__(self):
        # return f"<Sysop {self.fn.__name__} {self.args}>"
        # return f"{self.name} = {self.fn.__name__}{self.args}"
        args = " ".join([self.fn.__name__] + [str(a) for a in self.args])
        return f"({args})"


def compile(ast) -> list:
    """Transform an AST into a list of instructions"""


class Func(Callable):
    def __init__(self, fn):
        super().__init__(fn.__name__)
        self._fn = fn

    def __call__(self, *args, concurrent=False):
        # TODO concurrent
        # impl.push_args(*args)
        return impl.run(self.compile())
        # if Sysop.impl and Sysop.impl != impl:
        #     raise Exception(f"impl already set to {Sysop.impl}")
        # Sysop.impl = impl
        # return self._fn(*args)

    def compile(self) -> list:
        return compile_ast(self._fn())


class Sysop(Callable):
    impl = None

    def __init__(self, fn, *args):
        super().__init__(fn.__name__)
        self.fn = fn
        self.args = args

    def call(self, concurrent=False):
        # TODO concurrent
        return self.impl.eval(self.fn, self.args)


class If(Callable):
    # def __init__(self, cond, then, els):
    # def call
    # -> if ...
    pass


class Impl:
    pass
    # def eval


class TraceImpl(Impl):
    @staticmethod
    def eval(fn, *args):
        # for arg in args:
        #     if isinstance(arg, Future):
        #         print(f"FUTR {arg.name} (arg.source)")
        print(f"CALL {fn} ({args})")
        return None


# NOTE If polymorphism is allowed., a dependency graph may not be able to be
# drawn, and an AST must suffice...
class GraphImpl(Impl):
    @staticmethod
    def resolve(arg):
        if is_program(arg):
            return (arg.__name__, arg(GraphImpl))
        assert isinstance(arg, Future)
        return arg.name

    @staticmethod
    def call(fn, *args):
        assert isinstance(fn, callable)
        pass


# class GraphImpl can handle 'If' as a special-form function and traverse both
# branches explicitly.


def get_deps(c):
    assert isinstance(c, Sysop)
    res = []
    for arg in c.args:
        if isinstance(arg, Sysop):
            val = get_deps(arg)
        elif isinstance(arg, Future):
            # e.g. temp below
            # does Future know it's fn and args?
            # Want to preserve the input variable name
            # This should be building the graph, not just "deps"
            val = get_deps(arg.fn(arg.args))  # ????
        else:
            val = c
        res.append(val)
    return res


# -----


def plus1(x):
    return x + 1


def times2(x):
    return x * 2


def cube(x):
    return x ** 3


@Func
def times2_and_plus1(x):
    return Sysop(times2, Sysop(plus1, x))


@Func
def simple_prog(foo):
    temp = times2_and_plus1(foo)
    return Sysop(cube, temp)


@Func
def conc_prog(a, b):
    a_ = times2_and_plus1(a, concurrent=True)
    b_ = times2_and_plus1(b, concurrent=True)
    return Sysop(lambda a, b: a + b, a_, b_)


# ::::
# PUSH args[0] -- foo
# CALL plus1
# PUSH result -- unnamed
# CALL times2
# PUSH result -- temp
# CALL cube
# RETURN result
#
# foo -> times2_and_plus1     -> Sysop(cube)
#        x -> plus1 -> times2
#
# AST vs dependency graph??
# AST shows all syntactic elements, dep graph doesn't


@Func
def mapped_prog(foo_l):
    return Map(foo_l, times2_and_plus1)


# ::::
# PUSH args[0]
# PUSH times2_and_plus1
# (SUB Map)
#


# how to things out?? What does the AST / dep graph look like? One future per
# element? And a final function that takes them all?
def do_map(funcall, fn, lst):
    return [(i, funcall(fn, elt)) for i, elt in enumerate(lst)]


def do_collect(results):
    return [elt[1] for elt in sorted(results, key=lambda x: x[0])]


@Func
def Map(fn, lst):
    # TODO inject the "call" method here
    results = Sysop(do_map, something, fn, lst)
    return Sysop(do_collect, results)


##


def complex_fn(x):
    # time.sleep(random.randint(0, 2))
    return x * 2


def add(numbers):
    return sum(numbers)


def get_result(total, numbers):
    return [total, numbers]


@Func
def main(numbers):
    proc = Map(complex_fn, numbers)
    return get_result(add(proc), proc)


# When Map is called, it returns a Promise-thing / named channel
# When Map is called, it knows WHERE it's being called from, ie context
# When Map is called, it checks its arguments for promises
# It doesn't actually run the function unless the promises are resolved


def show_if():
    foo = get_foo()
    bar = If(foo, lambda: "yes", lambda: "no")
    # or, do 2k (or 2k+1) argument if statements (ie cond)
    return process_bar(bar)


def show_deconstruct():
    foo2 = get_foo2()
    return process2(First(foo2, 2), Rest(foo2, 3))


# Don't think you can draw graphs of if/then/else (branches). Depends on
# runtime.
# def If(cond, then, els): Sysop()


# Thus we get branching and control structures. What are the minimal primitives
# I need? Nil? Probably List, First, Rest... This IS a new language, embedded in
# python, and looks vaguely Lisp-ish. No need to decompile, just use run-time
# __call__ hooks.


# NOT USED:
class ProgramGraph:
    def __init__(self):
        self._graph = {}  # { node: ([ inputs ], [ outputs ]) }

    def add(self, node, inputs, outputs):
        assert isinstance(node, str)
        assert node not in self._graph
        self._graph[node] = ([], [])

    @property
    def nodes(self):
        return list(self._graph.keys())

    def outputs(self, node):
        return self._graph[node][1]

    def inputs(self, node):
        return self._graph[node][1]

    # def orphans(self):
    #     return

    def __iter__(self):
        for n in self.nodes:
            yield n


if __name__ == "__main__":
    # result = main([1, 2, 3, 4, 5])
    # print(result)
    # print(make_dot(times2_and_plus1))
    # print(times2_and_plus1(TraceImpl, "foo"))
    # print(simple_prog.call(1))
    print(conc_prog.compile())
