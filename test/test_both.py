from compiler import compile_all
from lang import *
from machine import LocalState, LocalMachine, Wait
from simple_functions import *
from test_machine import run_dbg_local
from test_compiler import list_defs


def check(defs: dict, data: LocalState, expected: LocalState):
    """Run a program to termination, and check that the data stack is as expected"""
    run_dbg_local(defs, data, trace=True)
    assert len(expected._ds) == len(data._ds)
    for i, (a, b) in enumerate(zip(expected._ds, data._ds)):
        assert i >= 0 and a == b


@Func
def simple_func(a, b):
    return a


@Func
def simple_func2(a):
    return simple_func(a, a)


def test_simple():
    @Func
    def main(a):
        return simple_func2(a)

    data = LocalState(5)
    expected = LocalState(5)
    compiled = compile_all(main)
    check(compiled, data, expected)


@Func
def xtimes2plus3(x):
    return FCall(lambda x: (2 * x) + 3, x)


@Func
def slow_math(x):
    return FCall(random_sleep_math, x)


@Func
def f_func(*args):
    return FCall(f, *args)


@Func
def resolve(a):
    return Asm([a], [Wait()])


def test_slow_math():
    """Test that execution works in the presence of random delays"""

    @Func
    def main(a):
        return Map(resolve, Map(slow_math, a))

    data = LocalState([1, 2, 3, 4, 5])
    expected = LocalState([5, 7, 9, 11, 13])
    compiled = compile_all(main)
    list_defs(compiled)
    check(compiled, data, expected)


if __name__ == "__main__":
    test_slow_math()
