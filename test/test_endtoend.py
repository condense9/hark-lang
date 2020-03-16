"""Test that programs run correctly - ie test both compiler and machine"""

from compiler import compile_all
from lang import *
from machine import LocalState, Wait
from simple_functions import *
from utils import run_dbg_local, list_defs, check_exec


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
    check_exec(compiled, data, expected)


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
    check_exec(compiled, data, expected)


if __name__ == "__main__":
    test_slow_math()
