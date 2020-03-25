"""Test that programs run correctly - ie test both compiler and machine"""

import time
import random
import c9c.machine as m
from c9c.compiler import compile_all, link
from c9c.lang import *
from c9c.runtime.local import LocalState, LocalRuntime, DebugProbe
from c9c.stdlib import Map, MapResolve, wait_for

from .simple_functions import *
from .utils import check_data, check_exec, list_defs


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

    input_val = 5
    expected_result = 5
    compiled = compile_all(main)
    executable = link(compile_all(main), exe_name="test_simple")
    # m.print_instructions(executable)

    runtime = LocalRuntime(executable, probe=DebugProbe)
    result = runtime.run(input_val)
    # for p in runtime.probes:
    #     p.print_logs()
    assert result == expected_result


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
        return MapResolve(slow_math, a)

    input_val = [1, 2]
    expected_result = [5, 7]
    executable = link(compile_all(main), exe_name="test_slow_math")
    m.print_instructions(executable)

    runtime = LocalRuntime(executable, probe=DebugProbe)
    result = runtime.run(input_val)
    for p in runtime.probes:
        p.print_logs()
    assert result == expected_result


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

    input_val = 5
    expected_result = [4, 4]
    executable = link(compile_all(main), exe_name="test_call_foreign")
    runtime = LocalRuntime(executable, probe=DebugProbe)
    result = runtime.run(input_val)
    assert result == expected_result


####################


def random_sleep():
    time.sleep(random.random() / 100.0)


def test_series_concurrent():
    """Designed to stress the concurrency model a bit more"""

    @Foreign
    def a(x):
        random_sleep()
        return x + 1

    @Foreign
    def b(x):
        random_sleep()
        return x * 1000

    @Foreign
    def c(x):
        random_sleep()
        return x - 1

    @Foreign
    def d(x):
        random_sleep()
        return x * 10

    @Foreign
    def h(u, v):
        return u - v

    @Func
    def main(x):
        return h(b(a(x)), d(c(x)))  # h(x) = (1000 * (x + 1)) - (10 * (x - 1))

    input_val = 5
    expected_result = 5960  # = 6000 - 40
    executable = link(compile_all(main), exe_name="series_concurrent")
    m.C9Machine.count = 0
    runtime = LocalRuntime(executable, probe=DebugProbe)
    try:
        result = runtime.run(input_val)
    finally:
        pass
        m.print_instructions(executable)
        for p in runtime.probes:
            p.print_logs()
    assert result == expected_result


if __name__ == "__main__":
    test_series_concurrent()
