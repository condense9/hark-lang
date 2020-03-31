"""Entrypoint for non-handler Machines - do not need to return anything"""

import json

from c9c.loader import load_executable
from c9c.runtime.aws import run_existing

import os.path

# Input: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
def handler(event, context):
    executable = load_executable(
        event["executable_name"], os.path.dirname(__file__) + "/" + "handlers"
    )
    run_existing(
        event["executable_name"], executable, event["session_id"], event["machine_id"]
    )
