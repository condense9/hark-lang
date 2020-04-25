import logging
import os
import sys

import c9.controllers.local as local

# import c9.controllers.ddb as ddb

from .parser.evaluate import evaluate_toplevel
from .parser.read import read_exp

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
        interface.add_def(name, code)

    for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
        interface.importpy(dest_name, mod_name, fn_name)


def run_local(filename, function, args):
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.Controller()
    interface = local.Interface(controller)
    toplevel = load_file(filename)
    args = [read_exp(arg) for arg in args]
    LOG.info("Running `%s` in %s", function, filename)
    LOG.info(f"Args: {args}")
    add_toplevel(interface, toplevel)

    try:
        interface.callf(function, args)
        interface.wait_for_finish()

    finally:
        LOG.debug(controller.executable.listing())
        for p in controller.probes:
            LOG.debug(f"probe {p}:\n" + "\n".join(p.logs))

        for i, outputs in enumerate(controller.outputs):
            print(f"--[Machine {i} Output]--")
            for (t, o) in outputs:
                print(f"{t:5.5f}  {o}")

    print("--RETURNED--")
    print(controller.result)


def run_ddb_local(filename, function, args):
    executor = ThreadExecutor()
    controller = ddb.Controller(executor, session)
    interface = ddb.Interface(controller)
    toplevel = load_file(filename)
    add_toplevel(interface, toplevel)

    interface.callf(function, args)

    print("--RETURNED--")
    print(controller.result)
