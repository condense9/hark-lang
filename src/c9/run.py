import logging
import os
import sys

import c9.controllers.local as local
import c9.executors.thread as thread

# import c9.controllers.ddb as ddb

from .parser.evaluate import evaluate_toplevel
from .parser.read import read_exp

LOG = logging.getLogger(__name__)


def load_file(filename):
    """Load and evaluate the contents of filename"""
    with open(filename) as f:
        content = f.read()

    return evaluate_toplevel(content)


def local_threaded():
    data_controller = local.DataController()
    invoker = local.ThreadInvoker(data_controller, local.Evaluator)
    interface = local.Interface(data_controller, invoker)
    return interface


def run_local(filename, function, args):
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    interface = local_threaded()
    toplevel = load_file(filename)
    interface.set_toplevel(toplevel)

    args = [read_exp(arg) for arg in args]
    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        controller = interface.data_controller
        interface.callf(function, args)
        thread.wait_for_finish(interface)

    finally:
        LOG.debug(controller.executable.listing())
        for p in controller.probes:
            LOG.debug(f"probe {p}:\n" + "\n".join(p.logs))

        for i, outputs in enumerate(controller.outputs):
            print(f"--[Machine {i} Output]--")
            for (t, o) in outputs:
                print(f"{t:5.5f}  {o}")

    print("--RETURNED--")
    print(controller.result)


def run_ddb_local(filename, function, args):
    executor = ThreadExecutor()
    controller = ddb.Controller(executor, session)
    interface = ddb.Interface(controller)
    toplevel = load_file(filename)
    interface.set_top(top_level)

    interface.callf(function, args)

    print("--RETURNED--")
    print(controller.result)
