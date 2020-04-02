"""Entrypoint for non-handler Machines - do not need to return anything"""

import sys
import os.path

sys.path.append("lib")

import c9.executors.awslambda
import c9.controllers.ddb
import c9.machine.c9e as c9e


def handler(event, context):
    # In the test, the zips are all named the same as their top level module
    exe_path = "executables/" + event["module_name"] + ".zip"
    assert os.path.exists(exe_path)
    executable = c9e.load(exe_path)
    run_method = c9.controllers.ddb.run_existing
    return c9.executors.awslambda.handler(run_method, executable, event, context)
