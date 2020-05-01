import logging
import time
import traceback
from typing import List

from .. import tealparser
from ..tealparser.read import read_exp

LOG = logging.getLogger(__name__)


class ThreadDied(Exception):
    """A Thread died (Teal machine thread, not necessarily a Python thread)"""


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
                    raise ThreadDied(f"{probe} forcibly stopped (steps: {probe.steps})")

            if invoker.exception:
                raise ThreadDied from invoker.exception.exc_value

    except Exception as e:
        LOG.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()


def run_and_wait(controller, invoker, waiter, filename, function, args: List[str]):
    """Run a function and wait for it to finish

    Arguments:
        controller: The Data Controller instance
        invoker:    The Machine invoker instance
        waiter:     A function to call to wait for the machine to finish
        filename:   The file to load
        function:   Name of the function to run
        args:       Arguments (as strings to be parsed) to pass in to function
    """
    toplevel = tealparser.load_file(filename)
    exe = tealparser.make_exe(toplevel)
    controller.set_executable(exe)

    # args = [read_exp(arg) for arg in args]

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        m = controller.new_machine(args, function, is_top_level=True)
        invoker.invoke(m, run_async=False)
        waiter(controller, invoker)

    finally:
        for p in controller.probes:
            LOG.info(f"probe {p}:\n" + "\n".join(p.logs))

        for i, outputs in enumerate(controller.stdout):
            print(f"--[Machine {i} Output]--")
            for o in outputs:
                print(o)

    print("--RETURNED--")
    print(controller.result)
