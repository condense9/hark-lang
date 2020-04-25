import threading
import warnings
import traceback
import time

from ..machine.probe import Probe


class ThreadExecutor:
    def __init__(self, target):
        threading.excepthook = self._threading_excepthook
        self.exception = None
        self.target = target

    def _threading_excepthook(self, args):
        self.exception = args

    def run(self, *args):
        # Awkward - we have to pass in self to the target, as the executor has
        # to be the first argument. TODO - clean up this interface.
        t = threading.Thread(target=self.target, args=[self, *args])
        t.run()


def wait_for_finish(interface, sleep_interval=0.01):
    data_controller = interface.data_controller
    invoker = interface.invoker
    try:
        while not data_controller.finished:
            time.sleep(sleep_interval)

            for probe in data_controller.probes:
                if isinstance(probe, Probe) and probe.early_stop:
                    raise Exception(f"{m} forcibly stopped by probe (too many steps)")

            if invoker.exception:
                raise ThreadDied from invoker.exception.exc_value

        if not all(
            data_controller.get_state(m).stopped for m in data_controller.machines
        ):
            raise Exception("Terminated, but not all machines stopped!")

    # except ThreadDied:
    #     raise

    except Exception as e:
        warnings.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()


class ThreadDied(Exception):
    """A thread died"""
