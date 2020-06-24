import logging
import sys
import time
import traceback
from typing import List

from .. import load
from ..machine import types as mt

LOG = logging.getLogger(__name__)


class ThreadDied(Exception):
    """A Thread died (Teal machine thread, not necessarily a Python thread)"""


def wait_for_finish(check_period, timeout, data_controller, invoker):
    """Wait for a machine to finish, checking every CHECK_PERIOD

    If timeout is None, wait indefinitely.

    """
    start_time = time.time()
    try:
        while not data_controller.all_stopped():
            time.sleep(check_period)
            if timeout and time.time() - start_time > timeout:
                raise Exception("Timeout waiting for finish")

            # This should never happen - we catch runtime errors and print them
            # nicely in machine
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

    args = [mt.TlString(a) for a in args]

    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")

    try:
        fn_ptr = exe.bindings[function]
    except KeyError:
        print(f"ERROR: Function `{function}` does not exist in {filename}!")
        return None

    try:
        m = controller.toplevel_machine(fn_ptr, args)
        invoker.invoke(m, run_async=False)
        waiter(controller, invoker)

    finally:
        for p in sorted(controller.get_probe_logs(), key=lambda p: p["thread"]):
            thread = p["thread"]
            log = p["log"]
            LOG.info(f"*** [{thread}] {log}")

    LOG.info(
        "DONE (broken? %s) [%s]: %s",
        controller.broken,
        type(controller.result),
        controller.result,
    )

    if not controller.broken:
        return controller.result

    # It broke - print traceback
    for vmid in controller.get_thread_ids():
        state = controller.get_state(vmid)
        err = state.error
        if err is not None:
            print(f"\nError [Thread {vmid}]: {err}")
            print("Teal Traceback (most recent call last):")
            for vmid, ip, fn in reversed(state.traceback):
                print(f"~ ({vmid}) {ip} - {fn}")
