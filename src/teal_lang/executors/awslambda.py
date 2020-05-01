import json
import logging
import os
import time

import boto3
import botocore

from .. import tealparser
from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..machine import TlMachine

RESUME_FN_NAME = os.environ.get("RESUME_FN_NAME", "resume")


def get_lambda_client():
    region = os.environ.get("TL_REGION", None)

    return boto3.client(
        "lambda",
        region_name=region,
        config=botocore.config.Config(retries={"max_attempts": 0}),
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
            session_id=self.data_controller.session.session_id,
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


def resume(event, context):
    """Handle the AWS lambda event for an existing session"""
    session_id = event["session_id"]
    vmid = event["vmid"]

    session = db.Session.get(session_id)
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = Invoker(controller)

    machine = TlMachine(vmid, invoker)
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


def new(event, context):
    """Create a new session"""
    function = event.get("function", "main")
    args = event.get("args", [])
    timeout = event.get("timeout", 10)
    check_period = event.get("check_period", 1)
    wait_for_finish = event.get("wait_for_finish", True)

    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = Invoker(controller)

    args = [tealparser.read_exp(arg) for arg in args]
    vmid = controller.new_machine(args, function, is_top_level=True)
    TlMachine(vmid, invoker).run()

    if wait_for_finish:
        start_time = time.time()
        while not controller.finished:
            time.sleep(check_period)
            if time.time() - start_time > timeout:
                raise Exception("Timeout waiting for finish")

    return json.dumps(
        dict(
            statusCode=200,
            body=dict(
                # --
                session_id=session.session_id,
                vmid=vmid,
                finished=controller.finished,
                result=controller.result,
            ),
        )
    )


def set_exe(event, context):
    """Set the executable for the base session"""
    db.init_base_session()
    content = event["content"]
    toplevel = tealparser.evaluate_toplevel(content)
    exe = tealparser.make_exe(toplevel)
    db.set_base_exe(exe)
    return dict(
        statusCode=200,
        body=dict(
            # --
            message="Base Executable set successfully"
        ),
    )
