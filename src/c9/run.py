import logging
import os
import sys

from c9.machine.interface import Interface
import c9.controllers.local as local
import c9.controllers.ddb as ddb_controller
import c9.controllers.ddb_model as db
import c9.executors.thread as c9_thread

from .parser.evaluate import evaluate_toplevel
from .parser.read import read_exp

LOG = logging.getLogger(__name__)


def load_file(filename):
    """Load and evaluate the contents of filename"""
    with open(filename) as f:
        content = f.read()

    return evaluate_toplevel(content)


def run_and_wait(interface, controller, waiter, filename, function, args):
    """Run a function and wait for it to finish

    Arguments:
        interface:  The Interface to use
        controller: The data controller instance
        waiter:     A function to call to wait on the interface
        filename:   File containing the program
        function:   Name of the function to run
        args:       Arguments to pass in to function
    """
    toplevel = load_file(filename)
    interface.set_toplevel(toplevel)

    args = [read_exp(arg) for arg in args]

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        interface.callf(function, args)
        waiter(interface)

    finally:
        LOG.debug(controller.executable.listing())
        for p in controller.probes:
            LOG.debug(f"probe {p}:\n" + "\n".join(p.logs))

        for i, outputs in enumerate(controller.stdout):
            print(f"--[Machine {i} Output]--")
            for o in outputs:
                print(o)

    print("--RETURNED--")
    print(controller.result)


def run_local(filename, function, args):
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.DataController()
    invoker = c9_thread.Invoker(controller, local.Evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(
        interface, controller, c9_thread.wait_for_finish, filename, function, args
    )


def run_ddb_local(filename, function, args):
    db.init()
    session = db.new_session()
    controller = ddb_controller.DataController(session)
    evaluator = ddb_controller.Evaluator
    invoker = c9_thread.Invoker(controller, evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(
        interface, controller, c9_thread.wait_for_finish, filename, function, args
    )
