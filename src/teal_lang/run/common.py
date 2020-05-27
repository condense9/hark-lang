import logging
import sys
import time
import traceback
from typing import List

from .. import load

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
    exe = load.compile_file(filename)
    controller.set_executable(exe)

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        fn_ptr = exe.bindings[function]
    except KeyError:
        raise ValueError(f"Function `{function}' does not exist!")

    try:
        m = controller.new_machine(args, fn_ptr, is_top_level=True)
        invoker.invoke(m, run_async=False)
        waiter(controller, invoker)

    finally:
        for p in controller.probes:
            LOG.info(f"probe {p}:\n" + "\n".join(p.logs))

        for item in controller.stdout:
            sys.stdout.write(item)
