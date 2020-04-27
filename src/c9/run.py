import logging
import os
import threading
import sys

from c9.machine.interface import Interface

from .parser.evaluate import evaluate_toplevel
from .parser.read import read_exp

LOG = logging.getLogger(__name__)


def load_file(filename):
    """Load and evaluate the contents of filename"""
    with open(filename) as f:
        content = f.read()

    return evaluate_toplevel(content)


def run_and_wait(interface, waiter, filename, function, args):
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
    import c9.controllers.local as local
    import c9.executors.thread as c9_thread

    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.DataController()
    invoker = c9_thread.Invoker(controller, local.Evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, c9_thread.wait_for_finish, filename, function, args)


def run_ddb_local(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.thread as c9_thread

    db.init()
    session = db.new_session()
    lock = threading.RLock()
    controller = ddb_controller.DataController(session, lock)
    evaluator = ddb_controller.Evaluator
    invoker = c9_thread.Invoker(controller, evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, c9_thread.wait_for_finish, filename, function, args)


def run_ddb_lambda_sim(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.lambdasim as lambdasim

    db.init()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session)
    evaluator = ddb_controller.Evaluator
    invoker = lambdasim.Invoker(controller, evaluator)
    interface = Interface(controller, invoker)
    run_and_wait(interface, lambdasim.wait_for_finish, filename, function, args)
