"""Invoke teal thread in a new lambda"""
import json
import logging
import os

import boto3
import botocore

# Teal "resume" lambda handler name. Should be set by the Teal deployment scripts.
RESUME_FN_NAME = os.environ["RESUME_FN_NAME"]


LOG = logging.getLogger(__name__)


def get_lambda_client():
    return boto3.client(
        "lambda", config=botocore.config.Config(retries={"max_attempts": 0}),
    )


class Invoker:
    def __init__(self, data_controller):
        self.data_controller = data_controller
        self.resume_fn_name = RESUME_FN_NAME
        self.exception = None

    def invoke(self, vmid, run_async=True):
        client = get_lambda_client()
        event = dict(
            # --
            session_id=self.data_controller.session_id,
            vmid=vmid,
        )
        res = client.invoke(
            # --
            FunctionName=self.resume_fn_name,
            InvocationType="Event",
            Payload=json.dumps(event),
        )
        if res["StatusCode"] != 202 or "FunctionError" in res:
            err = res["Payload"].read()
            # TODO retry!
            raise Exception(f"Invoke lambda {self.resume_fn_name} failed {err}")
