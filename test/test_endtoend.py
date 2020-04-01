"""Test that programs run correctly - ie test both compiler and machine"""

import logging
from os.path import join, dirname
import random
import time
import warnings

import pynamodb
import pytest

import c9.c9exe as c9exe
import c9.lambda_utils as lambda_utils
import c9.machine as m
import c9.runtime.ddb_threaded
import c9.runtime.local
from c9.compiler import compile_all, link
from c9.runtime.controllers import ddb
from c9.runtime.controllers.ddb_model import Session
from c9.runtime.executors import awslambda

from . import handlers
from .simple_functions import *

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
    "local": c9.runtime.local.run,
    "ddb_threaded": c9.runtime.ddb_threaded.run,
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
        if not lambda_utils.lambda_exists("c9run"):
            # `make build deploy` in $ROOT/c9_lambdas/c9run first
            warnings.warn("c9run lambda doesn't exit")
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
        c9exe.dump(filename, dest)


@pytest.mark.parametrize("handler", HANDLERS, ids=[h[0] for h in HANDLERS])
@pytest.mark.parametrize("runtime", RUNTIMES.values(), ids=RUNTIMES.keys())
def test_all_calls(handler, runtime):
    name = handler[0]
    input_val = handler[1]
    expected_result = handler[2]

    executable = c9exe.load(join(dirname(__file__), f"handlers/{name}.zip"))
    m.print_instructions(executable)
    try:
        controller = runtime(executable, input_val, do_probe=VERBOSE)
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
