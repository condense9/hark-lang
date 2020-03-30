"""Entrypoint for non-handler Machines - do not need to return anything"""

import json

from c9c.runtime.aws import run


# Input: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
def handler(event, context):
    body = json.loads(event["body"])
    run_existing(body["session_id"], body["machine_id"])
