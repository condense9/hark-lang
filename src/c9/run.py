import logging
import os
import sys
import threading
import time
import traceback
from functools import partial

from . import parser
from .parser.read import read_exp

LOG = logging.getLogger(__name__)


class ThreadDied(Exception):
    """A Thread died (C9 machine thread, not necessarily a Python thread)"""


def wait_for_finish(check_period, timeout, data_controller, invoker):
    """Wait for a machine to finish, checking every CHECK_PERIOD"""
    start_time = time.time()
    try:
        while not data_controller.finished:
            time.sleep(check_period)
            if time.time() - start_time > timeout:
                raise Exception("Timeout waiting for finish")

            for probe in data_controller.probes:
                if probe.early_stop:
                    raise ThreadDied(f"{m} forcibly stopped by probe (too many steps)")

            if invoker.exception:
                raise ThreadDied from invoker.exception.exc_value

    except Exception as e:
        LOG.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()


def run_and_wait(controller, invoker, waiter, filename, function, args):
    """Run a function and wait for it to finish

    Arguments:
        controller: The Data Controller instance
        invoker:    The Machine invoker instance
        waiter:     A function to call to wait for the machine to finish
        filename:   The file to load
        function:   Name of the function to run
        args:       Arguments to pass in to function
    """
    toplevel = parser.load_file(filename)
    exe = parser.make_exe(toplevel)
    controller.set_executable(exe)

    args = [read_exp(arg) for arg in args]

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        m = controller.new_machine(args, function, is_top_level=True)
        invoker.invoke(m, run_async=False)
        waiter(controller, invoker)

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
    invoker = c9_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 0.1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)


def run_ddb_local(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.thread as c9_thread

    db.init()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = c9_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)


def run_ddb_processes(filename, function, args):
    import c9.controllers.ddb as ddb_controller
    import c9.controllers.ddb_model as db
    import c9.executors.multiprocess as mp

    db.init()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = mp.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)


def setup_base_session(filename):
    db.init()
    toplevel = parser.load_file(filename)
    exe = parser.make_exe(toplevel)
    db.set_base_exe(exe)


def run_lambda(function, args):
    run_and_wait()


# create the infra
# set the base session
# run a function with some args
