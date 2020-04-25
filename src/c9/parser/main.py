import logging
import os
import sys

import c9.controllers.local as local
import lark

from .evaluate import evaluate_toplevel
from .load import file_parser
from .read import ReadLiterals

LOG = logging.getLogger(__name__)


def run(controller, filename, function, args):
    """Load and run a function"""
    with open(filename) as f:
        content = f.read()

    toplevel = evaluate_toplevel(content)

    # print(toplevel.defs)
    # print(toplevel.foreigns)

    for name, code in toplevel.defs.items():
        controller.def_(name, code)

    for dest_name, (fn_name, mod_name) in toplevel.foreigns.items():
        controller.importpy(dest_name, mod_name, fn_name)

    # print(controller.executable.listing())

    controller.callf(function, args)


def run_local(filename, function, args):
    LOG.info("Running `%s` in %s", function, filename)
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.LocalController()

    try:
        run(controller, filename, function, args)
        local.wait_for_finish(controller)

    finally:
        for i, outputs in enumerate(controller.outputs):
            print(f"--[Machine {i} Output]--")
            for (t, o) in outputs:
                print(f"{t:5.5f}  {o}")

    print("--RESULT--")
    print(controller.result)


def graph(filename, function, dest_png):
    with open(filename) as f:
        content = f.read()

    parser = file_parser()
    tree = parser.parse(content)
    ast = ReadLiterals().transform(tree)
    for c in ast.children:
        if c.data == "def_" and c.children[0] == function:
            lark.tree.pydot__tree_to_png(c, dest_png)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # FIXME can't pass args on commandline yet
    run_local(sys.argv[1], sys.argv[2], [])
