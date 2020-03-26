"""Test that programs run correctly - ie test both compiler and machine"""

import random
import time

import pytest

import c9c.machine as m
from c9c.compiler import compile_all, link
from c9c.lang import *
import c9c.runtime.local as local
from c9c.stdlib import Map, MapResolve, wait_for

from .simple_functions import *


SEED = random.randint(0, 100000)
random.seed(SEED)
print("Random seed", SEED)


def random_sleep():
    time.sleep(random.random() / 100.0)


def test_all_calls():
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

    input_val = 5
    expected_result = 5
    compiled = compile_all(main)
    executable = link(compile_all(main), exe_name="all_calls")
    try:
        storage = local.run(executable, input_val, do_probe=True)
    finally:
        m.print_instructions(executable)
    result = storage.result
    assert result == expected_result


####################


def test_mapping():
    """Test that mapping works in the presence of random delays"""

    @Foreign
    def random_sleep_math(x):
        random_sleep()
        return (2 * x) + 3

    @Func
    def main(a):
        return MapResolve(random_sleep_math, a)

    input_val = [1, 2]
    expected_result = [5, 7]
    executable = link(compile_all(main), exe_name="test_slow_math")
    try:
        storage = local.run(executable, input_val, do_probe=True)
    finally:
        m.print_instructions(executable)
        for p in storage.probes:
            p.print_logs()
    result = storage.result
    assert result == expected_result


####################


def test_call_foreign():
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

    input_val = 5
    expected_result = [4, 4]
    executable = link(compile_all(main), exe_name="test_call_foreign")
    try:
        storage = local.run(executable, input_val, do_probe=True)
    finally:
        m.print_instructions(executable)
        for p in storage.probes:
            p.print_logs()
    result = storage.result
    assert result == expected_result


####################

# Test more:
# env PYTHONPATH=src pytest -vv -x --count 5 test/test_endtoend.py
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
    try:
        storage = local.run(executable, input_val, do_probe=True)
    finally:
        m.print_instructions(executable)
        for p in storage.probes:
            p.print_logs()
    result = storage.result
    assert result == expected_result


if __name__ == "__main__":
    test_series_concurrent()
