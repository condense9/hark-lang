"""Build a machine executable from a top-level AST"""

import logging

from ..machine import Executable

LOG = logging.getLogger(__name__)


def make_exe(toplevel):
    defs = {}
    foreign = {}

    def _build_exe():
        location = 0
        code = []
        locations = {}
        for fn_name, fn_code in defs.items():
            locations[fn_name] = location
            code += fn_code
            location += len(fn_code)
        return Executable(locations, foreign, code)

    def _add_def(name, code):
        # If any machines are running, they will break!
        LOG.info("Defining `%s` (%d instructions)", name, len(code))
        defs[name] = code

    def _importpy(dest_name, mod_name, fn_name):
        LOG.info("Importing `%s` from %s", fn_name, mod_name)
        foreign[dest_name] = [fn_name, mod_name]

    for name, code in toplevel.defs.items():
        _add_def(name, code)

    for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
        _importpy(dest_name, mod_name, fn_name)

    return _build_exe()
