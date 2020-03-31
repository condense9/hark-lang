"""Test that programs run correctly - ie test both compiler and machine"""

import logging
import os.path
import random
import time
import warnings

import pynamodb
import pytest

import c9c.lambda_utils as lambda_utils
import c9c.machine as m
import c9c.runtime.ddb_threaded
import c9c.runtime.local
from c9c.compiler import compile_all, link
from c9c.runtime.controllers import ddb
from c9c.runtime.controllers.ddb_model import Session
from c9c.runtime.executors import awslambda

from . import handlers
from .simple_functions import *

THIS_DIR = os.path.dirname(__file__)

SEED = random.randint(0, 100000)
random.seed(SEED)
print("Random seed", SEED)

logging.basicConfig(level=logging.INFO)


def run_ddb_lambda_test(exe_name, searchpath, input_val, **kwargs):
    executor = awslambda.LambdaRunner("c9run")
    return ddb.run(
        executor,
        exe_name,
        "handlers",
        input_val,
        timeout=60,
        sleep_interval=2,
        **kwargs,
    )


RUNTIMES = {
    # --
    "local": c9c.runtime.local.run,
    "ddb_threaded": c9c.runtime.ddb_threaded.run,
    "ddb_lambda": run_ddb_lambda_test,
}


def setup_module():
    if not lambda_utils.lambda_exists("c9run"):
        # `make build deploy` in $ROOT/c9_lambdas/c9run first
        warnings.warn("c9run lambda doesn't exit")
    try:
        if Session.exists():
            Session.delete_table()
        Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    except pynamodb.exceptions.PynamoDBConnectionError:
        # It's not actually essential for testing local...
        warnings.warn("Can't connect to DynamoDB table")


def check_result(runtime, main, input_val, expected_result, exe_name, verbose=True):
    """Run main with input_val, check that result is expected_result"""
    executable = link(compile_all(main), exe_name=exe_name)
    m.print_instructions(executable)
    try:
        sp = os.path.dirname(__file__) + "/" + "handlers"
        controller = runtime(exe_name, sp, input_val, do_probe=verbose)
    finally:
        if verbose:
            print(f"-- LOGS ({len(controller.probes)} probes)")
            for p in controller.probes:
                print("\n".join(p.logs))
                print("")
            print("-- END LOGS")
    if not controller.finished:
        warnings.warn("Controller did not finish - this will fail")
    assert controller.result == expected_result


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(runtime):
    """Test all kinds of call - normal, foreign, and async"""
    main = handlers.all_calls.main
    check_result(runtime, main, 5, 5, "all_calls")


####################


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_mapping(runtime):
    """Test that mapping works in the presence of random delays"""
    main = handlers.mapping.main
    check_result(runtime, main, [1, 2], [5, 7], "mapping")


####################


@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_call_foreign(runtime):
    """More foreign call tests"""
    main = handlers.call_foreign.main
    check_result(runtime, main, 5, [4, 4], "call_foreign")


####################

# Test more:
# env PYTHONPATH=src pytest -vv -x --count 5 test/test_endtoend.py
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_series_concurrent(runtime):
    """Designed to stress the concurrency model a bit more"""
    main = handlers.series_concurrent.main
    input_val = 5
    expected_result = 5960  # = 6000 - 40
    check_result(runtime, main, input_val, expected_result, "series_concurrent")
