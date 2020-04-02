"""Test that programs run correctly - ie test both compiler and machine"""

import logging
import random
import time
import warnings
from os.path import dirname, join

import pynamodb
import pytest

import c9.lambda_utils as lambda_utils
import c9.machine as m
import c9.py_to_c9e as py_to_c9e
import c9.runtimes.ddb_lambda
import c9.runtimes.ddb_threaded
import c9.runtimes.local
from c9.compiler import compile_all, link
from c9.controllers import ddb
from c9.controllers.ddb_model import Session
from c9.executors import awslambda
from c9.machine import c9e

from . import handlers
from .simple_functions import *

SEED = random.randint(0, 100000)
random.seed(SEED)
print("Random seed", SEED)

logging.basicConfig(level=logging.INFO)


def run_ddb_lambda_test(exe_name, input_value, do_probe):
    """Simple wrapper around ddb_lambda.run specifically for the test lambda"""
    assert lambda_utils.lambda_exists("runtest")
    return c9.runtimes.ddb_lambda.run(
        "runtest",
        exe_name,
        input_value,
        do_probe=do_probe,
        timeout=60,
        sleep_interval=2,
    )


RUNTIMES = {
    # --
    "local": c9.runtimes.local.run,
    "ddb_threaded": c9.runtimes.ddb_threaded.run,
    "ddb_lambda": run_ddb_lambda_test,
}


HANDLERS = [
    ("all_calls", 5, 5),
    ("conses", 2, [1, 2, 3, 4]),
    ("mapping", [1, 2], [5, 7]),
    ("call_foreign", 5, [4, 4]),
    ("series_concurrent", 5, 5960),
]

VERBOSE = True


def setup_module():
    try:
        if Session.exists():
            Session.delete_table()
        Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    except:
        # It's not actually essential for testing local...
        warnings.warn("Can't connect to DynamoDB table")

    for h in HANDLERS:
        name = h[0]
        filename = join(dirname(__file__), "handlers", f"{name}.py")
        dest = join(dirname(__file__), f"handlers/{name}.zip")
        py_to_c9e.dump(filename, dest)


@pytest.mark.parametrize("handler", HANDLERS, ids=[h[0] for h in HANDLERS])
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(handler, runtime):
    name = handler[0]
    input_val = handler[1]
    expected_result = handler[2]
    path_to_exe = join(dirname(__file__), f"handlers/{name}.zip")

    if VERBOSE:
        executable = c9e.load(path_to_exe)
        m.print_instructions(executable)

    try:
        controller = runtime(path_to_exe, [input_val], do_probe=VERBOSE)
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
