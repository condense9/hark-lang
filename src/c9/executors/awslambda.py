import json
import logging
import os
from os.path import join

from .. import constants
from ..lambda_utils import get_lambda_client
from ..machine import c9e


class LambdaExecutor:
    def __init__(self, fn_name):
        self.fn_name = fn_name
        self.exception = None

    def invoke(self, vmid, run_async=True):
        client = get_lambda_client()
        event = dict(
            # --
            session_id=self.data_controller.session.session_id,
            vmid=vmid,
        )
        res = client.invoke(
            # --
            FunctionName=self.fn_name,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        if res["StatusCode"] != 202 or "FunctionError" in res:
            err = res["Payload"].read()
            # TODO retry!
            raise Exception(f"Invoke lambda {self.fn_name} failed {err}")


def handler(event, context):
    """Handle the AWS lambda event for a new session"""
    session_id = event["session_id"]
    vmid = event["vmid"]

    session = db.Session.get(session_id)
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = Invoker(controller)

    machine = C9Machine(vmid, invoker)
    machine.run()

    return json.dumps(
        dict(
            statusCode=200,
            body=dict(
                # --
                session_id=session_id,
                vmid=vmid,
                finished=controller.finished,
                result=controller.result,
            ),
        )
    )
