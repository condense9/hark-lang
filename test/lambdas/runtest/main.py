"""Entrypoint for non-handler Machines - do not need to return anything"""

import sys

sys.path.append("lib")

import c9.runtime.executors.awslambda
import c9.runtime.controllers.ddb
import c9.machine.c9e


def handler(event, context):
    executable = c9e.load()
    getter = c9c.runtime.controllers.ddb.run_existing
    return c9c.runtime.executors.awslambda.handler(getter, event, context)
