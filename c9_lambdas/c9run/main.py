"""Entrypoint for non-handler Machines - do not need to return anything"""

import sys

sys.path.append("lib")

import c9c.runtime.executors.awslambda
import c9c.runtime.controllers.ddb


def handler(event, context):
    getter = c9c.runtime.controllers.ddb.run_existing
    return c9c.runtime.executors.awslambda.handler(getter, event, context)
