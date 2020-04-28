import logging
import os
import threading
import traceback
import time
import sys

from c9.machine.interface import Interface

from .parser.evaluate import evaluate_toplevel
from .parser.read import read_exp

LOG = logging.getLogger(__name__)


class ThreadDied(Exception):
    """A Thread died (C9 machine thread, not necessarily a Python thread)"""


def load_file(filename):
    """Load and evaluate the contents of filename"""
    with open(filename) as f:
        content = f.read()

    return evaluate_toplevel(content)


def wait_for_finish(check_period, interface):
    """Wait for a machine to finish, checking every CHECK_PERIOD"""
    data_controller = interface.data_controller
    invoker = interface.invoker
    try:
        while not data_controller.finished:
            time.sleep(check_period)

            for probe in data_controller.probes:
                if probe.early_stop:
                    raise ThreadDied(f"{m} forcibly stopped by probe (too many steps)")

            if invoker.exception:
                raise ThreadDied from invoker.exception.exc_value

    except Exception as e:
        LOG.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()


def run_and_wait(interface, filename, function, args, check_period=0.01):
    """Run a function and wait for it to finish

    Arguments:
        interface:  The Interface to use
        controller: The data controller instance
        waiter:     A function to call to wait on the interface
        filename:   File containing the program
        function:   Name of the function to run
        args:       Arguments to pass in to function
    """
    controller = interface.data_controller
    toplevel = load_file(filename)
    interface.set_toplevel(toplevel)

    args = [read_exp(arg) for arg in args]

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        m = controller.new_machine(args, function, is_top_level=True)
        interface.invoker.invoke(m, run_async=False)
        wait_for_finish(check_period, interface)

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
    import c9.controllers.local as local
    import c9.executors.thread as c9_thread

    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.DataController()
    invoker = c9_thread.Invoker(controller, local.Evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, filename, function, args)


def run_ddb_local(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.thread as c9_thread

    db.init()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    evaluator = ddb_controller.Evaluator
    invoker = c9_thread.Invoker(controller, evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, filename, function, args, 1)


def run_ddb_lambda_sim(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.lambdasim as lambdasim

    db.init()
    session = db.new_session()
    lock = db.SessionLocker(session)

    # controller = ddb_controller.DataController(session, lock)
    # evaluator = ddb_controller.Evaluator
    # invoker = lambdasim.Invoker(controller, evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, lambdasim.wait_for_finish, filename, function, args)
