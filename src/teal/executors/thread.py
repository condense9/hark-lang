import threading
import warnings
import traceback
import time

from ..machine.probe import Probe
from ..machine import TlMachine


class Invoker:
    def __init__(self, data_controller):
        self.data_controller = data_controller
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def invoke(self, vmid, run_async=True):
        m = TlMachine(vmid, self)
        if run_async:
            thread = threading.Thread(target=m.run)
            thread.start()
        else:
            m.run()
