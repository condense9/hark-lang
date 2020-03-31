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
    # This will make us a new session :)
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


####################

HANDLERS = [
    ("all_calls", handlers.all_calls.main, 5, 5),
    ("conses", handlers.conses.main, 2, [1, 2, 3, 4]),
    ("mapping", handlers.mapping.main, [1, 2], [5, 7]),
    ("call_foreign", handlers.call_foreign.main, 5, [4, 4]),
    ("series_concurrent", handlers.series_concurrent.main, 5, 5960),
]


@pytest.mark.parametrize("handler", HANDLERS, ids=[h[0] for h in HANDLERS])
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(handler, runtime):
    name = handler[0]
    main = handler[1]
    input_val = handler[2]
    expected_result = handler[3]
    check_result(runtime, main, input_val, expected_result, name)
