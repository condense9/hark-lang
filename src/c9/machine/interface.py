"""Top-level machine control interface"""

import logging

from .executable import Executable
from ..parser.make_exe import make_exe

LOG = logging.getLogger(__name__)


class Interface:
    def __init__(self, data_controller, invoker):
        self.invoker = invoker
        self.data_controller = data_controller

    def set_toplevel(self, toplevel):
        exe = make_exe(toplevel)
        self.data_controller.set_executable(exe)
