"""Test that programs run correctly - ie test both compiler and machine"""

import random
import time

import pytest

import c9c.machine as m
from c9c.compiler import compile_all, link
from c9c.lang import *
import c9c.runtime.local

# import c9c.runtime.aws
from c9c.stdlib import Map, MapResolve, wait_for

from .simple_functions import *


SEED = random.randint(0, 100000)
random.seed(SEED)
print("Random seed", SEED)


RUNTIMES = {
    "local": c9c.runtime.local,
    # "aws": c9c.runtime.aws
}


def random_sleep(max_ms=10):
    time.sleep(max_ms * random.random() / 1000.0)


def check_result(runtime, main, input_val, expected_result, exe_name, verbose=True):
    """Run main with input_val, check that result is expected_result"""
    executable = link(compile_all(main), exe_name=exe_name)
    try:
        storage = runtime.run(executable, input_val, do_probe=True)
    finally:
        if verbose:
            m.print_instructions(executable)
            for p in storage.probes:
                p.print_logs()
    assert storage.result == expected_result


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(runtime):
    """Test all kinds of call - normal, foreign, and async"""

    @Foreign
    def do_sleep(x):
        random_sleep()
        return x

    @Func
    def level2(a, b):
        return do_sleep(a)

    @AsyncFunc
    def level1(a):
        return level2(a, a)

    @Func
    def main(a):
        return level1(a)

    check_result(runtime, main, 5, 5, "all_calls")


####################


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_mapping(runtime):
    """Test that mapping works in the presence of random delays"""

    @Foreign
    def random_sleep_math(x):
        random_sleep()
        return (2 * x) + 3

    @Func
    def main(a):
        return MapResolve(random_sleep_math, a)

    check_result(runtime, main, [1, 2], [5, 7], "slow_math")


####################


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_call_foreign(runtime):
    """More foreign call tests"""

    @Foreign
    def simple_math(x):
        return x - 1

    @Func
    def call_foreign(x):
        return Cons(simple_math(x), simple_math(x))

    @Func
    def main(x):
        # The rules:
        # - main will wait on the value returned
        # - you cannot wait on a list that contains futures
        # - the programmer must wait on all elements
        # SO this is illegal:
        #   return call_foreign(x)
        # ...because call_foreign returns a Cons of futures
        return Map(wait_for, call_foreign(x))

    check_result(runtime, main, 5, [4, 4], "call_foreign")


####################

# Test more:
# env PYTHONPATH=src pytest -vv -x --count 5 test/test_endtoend.py
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_series_concurrent(runtime):
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
    check_result(runtime, main, input_val, expected_result, "series_concurrent")
