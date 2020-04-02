"""Entrypoint for non-handler Machines - do not need to return anything"""

import sys

sys.path.append("lib")

import c9.runtime.executors.awslambda
import c9.runtime.controllers.ddb
import c9.machine.c9e


def handler(event, context):
    # In the test, the zips are all named the same as their top level module
    executable = c9e.load(event["module_name"] + ".zip")
    run_method = c9c.runtime.controllers.ddb.run_existing
    return c9c.runtime.executors.awslambda.handler(
        run_method, executable, event, context
    )
