"""Test that programs run correctly - ie test both compiler and machine"""

import logging
import os
import random
import time
import warnings
from os.path import dirname, join

import pynamodb
import pytest

import c9.lambda_utils as lambda_utils
import c9.machine as m
import c9.runtimes.ddb_lambda
import c9.runtimes.ddb_threaded
import c9.runtimes.local
from c9.compiler import compile_all, link
from c9.controllers import ddb
from c9.controllers.ddb_model import Session
from c9.executors import awslambda
from c9.machine import c9e

from .handlers.src import all_calls, call_foreign, conses, mapping, series_concurrent
from .simple_functions import *

SEED = random.randint(0, 100000)
random.seed(SEED)
print("Random seed", SEED)

logging.basicConfig(level=logging.INFO)

# pytestmark = pytest.mark.skipif(
#     "SKIP_E2E" in os.environ, reason="Found SKIP_E2E in env vars"
# )

pytestmark = pytest.mark.skip(
    "Not updated to use new grammar - test manually with examples/hello for now"
)


def setup_module():
    try:
        if Session.exists():
            Session.delete_table()
        Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    except:
        # It's not actually essential for testing local...
        warnings.warn("Can't connect to DynamoDB table")


def run_ddb_lambda_test(executable, input_value, do_probe):
    """Simple wrapper around ddb_lambda.run specifically for the test lambda"""
    assert lambda_utils.lambda_exists("runtest")
    return c9.runtimes.ddb_lambda.run(
        "runtest",
        executable,
        input_value,
        do_probe=do_probe,
        timeout=60,
        sleep_interval=2,
    )


VERBOSE = True

RUNTIMES = {
    # --
    "local": c9.runtimes.local.run,
    "ddb_threaded": c9.runtimes.ddb_threaded.run,
    "ddb_lambda": run_ddb_lambda_test,
}

# from .handlers import all_calls, call_foreign, conses, mapping, series_concurrent
HANDLERS = [
    ("all_calls", all_calls.main, 5, 5),
    ("conses", conses.main, 2, [1, 2, 3, 4]),
    ("mapping", mapping.main, [1, 2], [5, 7]),
    ("call_foreign", call_foreign.main, 5, [4, 4]),
    ("series_concurrent", series_concurrent.main, 5, 5960),
]


@pytest.mark.parametrize("handler", HANDLERS, ids=[h[0] for h in HANDLERS])
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(handler, runtime):
    name = handler[0]
    entrypoint = handler[1]
    input_val = handler[2]
    expected_result = handler[3]
    executable = link(compile_all(entrypoint), name)

    if VERBOSE:
        m.print_instructions(executable)

    try:
        controller = runtime(executable, [input_val], do_probe=VERBOSE)
    finally:
        if VERBOSE:
            print(f"-- LOGS ({len(controller.probes)} probes)")
            for p in controller.probes:
                print("\n".join(p.logs))
                print("")
            print("-- END LOGS")
    if not controller.finished:
        warnings.warn("Controller did not finish - this will fail")
    assert controller.result == expected_result


# def test_bla():
