"""Test that programs run correctly - ie test both compiler and machine"""

from compiler import compile_all, link
from lang import *
from machine import LocalState, Wait
from simple_functions import *
from utils import list_defs, check_exec
from stdlib import wait_for, Map


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
    check_exec(link(compiled), data, expected)


####################

@Func
def xtimes2plus3(x):
    return ForeignCall(lambda x: (2 * x) + 3, x)


@Func
def slow_math(x):
    return ForeignCall(random_sleep_math, x)


@Func
def f_func(*args):
    return ForeignCall(f, *args)


def test_slow_math():
    """Test that execution works in the presence of random delays"""

    @Func
    def main(a):
        return Map(wait_for, Map(slow_math, a))

    data = LocalState([1, 2, 3, 4, 5])
    expected = LocalState([5, 7, 9, 11, 13])
    compiled = compile_all(main)
    list_defs(compiled)
    check_exec(link(compiled), data, expected)


####################

@Foreign
def simple_math(x):
    return x - 1


@Func
def call_foreign(x):
    return Cons(simple_math(x), simple_math(x))


def test_call_foreign():
    @Func
    def main(x):
        return Map(wait_for, call_foreign(x))

    data = LocalState(5)
    expected = LocalState([4, 4])
    compiled = compile_all(main)
    # list_defs(compiled)
    check_exec(link(compiled), data, expected)

if __name__ == "__main__":
    test_slow_math()
