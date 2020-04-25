import logging
import os
import sys

import c9.controllers.local as local

from .parser.evaluate import evaluate_toplevel

LOG = logging.getLogger(__name__)


def load_file(filename):
    """Load and evaluate the contents of filename"""
    with open(filename) as f:
        content = f.read()

    return evaluate_toplevel(content)


def add_toplevel(interface, toplevel):
    """Load toplevel definitions into controller"""
    LOG.debug(toplevel.defs)
    LOG.debug(toplevel.foreigns)

    for name, code in toplevel.defs.items():
        interface.def_(name, code)

    for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
        interface.importpy(dest_name, mod_name, fn_name)


def run_local(filename, function, args):
    LOG.info("Running `%s` in %s", function, filename)
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.Controller()
    interface = local.Interface(controller)

    try:
        toplevel = load_file(filename)
        add_toplevel(interface, toplevel)

        interface.callf(function, args)
        local.wait_for_finish(controller)

    finally:
        LOG.debug(controller.executable.listing())
        for i, outputs in enumerate(controller.outputs):
            print(f"--[Machine {i} Output]--")
            for (t, o) in outputs:
                print(f"{t:5.5f}  {o}")

    print("--RETURNED--")
    print(controller.result)
