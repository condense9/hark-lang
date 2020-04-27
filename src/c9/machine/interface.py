"""Top-level machine control interface"""

import logging

from .executable import Executable

LOG = logging.getLogger(__name__)


class Interface:
    def __init__(self, data_controller, invoker):
        self.invoker = invoker
        self.data_controller = data_controller
        self.defs = {}
        self.foreign = {}

    # User interface
    def _build_exe(self):
        location = 0
        code = []
        locations = {}
        for fn_name, fn_code in self.defs.items():
            locations[fn_name] = location
            code += fn_code
            location += len(fn_code)
        return Executable(locations, self.foreign, code)

    def _add_def(self, name, code):
        # If any machines are running, they will break!
        LOG.info("Defining `%s` (%d instructions)", name, len(code))
        self.defs[name] = code

    def _importpy(self, dest_name, mod_name, fn_name):
        LOG.info("Importing `%s` from %s", fn_name, mod_name)
        self.foreign[dest_name] = [fn_name, mod_name]

    def set_toplevel(self, toplevel):
        for name, code in toplevel.defs.items():
            self._add_def(name, code)

        for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
            self._importpy(dest_name, mod_name, fn_name)

        exe = self._build_exe()
        self.data_controller.set_executable(exe)
