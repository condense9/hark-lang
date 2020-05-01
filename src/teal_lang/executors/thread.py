import logging
import threading
import time
import traceback
import warnings

from ..machine import TlMachine

LOG = logging.getLogger(__name__)


class Invoker:
    def __init__(self, data_controller):
        self.data_controller = data_controller
        self.exception = None
        threading.excepthook = self._threading_excepthook

    def _threading_excepthook(self, args):
        self.exception = args

    def invoke(self, vmid, run_async=True):
        LOG.info(f"Invoking {vmid} (new thread? {run_async})")
        m = TlMachine(vmid, self)
        if run_async:
            thread = threading.Thread(target=m.run)
            LOG.info(f"New thread: {thread}")
            thread.start()
        else:
            m.run()
