"""Entrypoint for non-handler Machines - do not need to return anything"""

import sys
import os.path
from os.path import join, dirname

sys.path.append("lib")

import c9.executors.awslambda
import c9.controllers.ddb
import c9.machine.c9e as c9e


def handler(event, context):
    run_method = c9.controllers.ddb.run_existing

    # In the test, the zips are all named the same as their top level module
    zipfile = "executables/" + event["module_name"] + ".zip"

    executable = c9e.load(zipfile, [join(dirname(__file__), "src")])

    return c9.executors.awslambda.handler(run_method, executable, event, context)
