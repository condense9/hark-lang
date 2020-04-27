import threading
import warnings
import traceback
import time

from ..machine.probe import Probe
from ..machine import C9Machine


class Invoker:
    def __init__(self, data_controller, evaluator_cls):
        self.data_controller = data_controller
        self.evaluator_cls = evaluator_cls
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def invoke(self, vmid, run_async=True):
        m = C9Machine(vmid, self)
        if run_async:
            thread = threading.Thread(target=m.run)
            thread.start()
        else:
            m.run()


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

    # except ThreadDied:
    #     raise

    except Exception as e:
        warnings.warn("Unexpected Exception!! Returning controller for analysis")
        traceback.print_exc()


class ThreadDied(Exception):
    """A thread died"""
