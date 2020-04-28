import json
import logging
import os
import time
from os.path import join

from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..lambda_utils import get_lambda_client
from ..c9parser.evaluate import evaluate_toplevel

RESUME_FN_NAME = os.environ.get("RESUME_FN_NAME", "resume")


class Invoker:
    def __init__(self):
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
            Payload=json.dumps(payload),
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

    args = [read_exp(arg) for arg in args]
    vmid = controller.new_machine(args, function, is_top_level=True)
    C9Machine(vmid, invoker).run()

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
                session_id=session_id,
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
    toplevel = evaluate_toplevel(content)
    exe = parser.make_exe(toplevel)
    db.set_base_exe(exe)
