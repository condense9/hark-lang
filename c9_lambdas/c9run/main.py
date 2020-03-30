"""Entrypoint for non-handler Machines - do not need to return anything"""

import json

from c9c.loader import load_executable
from c9c.runtime.aws import run_existing


# Input: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
def handler(event, context):
    executable = load_executable("handlers." + event["executable_name"])
    run_existing(executable, event["session_id"], event["machine_id"])
