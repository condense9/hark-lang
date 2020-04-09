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

    def run(self, executable, session_id, machine_id, do_probe):
        client = get_lambda_client()
        logging.info("Running lambda for executable: %s", executable.name)
        payload = dict(
            lambda_name=self.fn_name,
            executable_name=executable.name,
            session_id=session_id,
            machine_id=machine_id,
            do_probe=do_probe,
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
            raise Exception(f"Invoke lambda failed {err}")


# Input: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
def handle_existing(run_controller, event, context):
    """Handle the AWS lambda event for an existing session, returning a JSON response"""
    logging.info(f"Invoked - {event}")

    zipfile = join(constants.EXE_PATH, event["executable_name"] + ".c9e")
    executable = c9e.load(zipfile, [constants.SRC_PATH, constants.LIB_PATH])

    executor = LambdaExecutor(event["lambda_name"])
    controller = run_controller(
        executor,
        executable,
        event["session_id"],
        event["machine_id"],
        event["do_probe"],
    )
    if controller.finished:
        return json.dumps(
            dict(
                session_id=event["session_id"],
                machine_id=event["machine_id"],
                finished=True,
                result=controller.result,
            )
        )
    else:
        return json.dumps(
            dict(
                session_id=event["session_id"],
                machine_id=event["machine_id"],
                finished=False,
            )
        )


def handle_new(run_controller, event, context):
    """Handle the AWS lambda event for a new session"""
    handler_name = os.environ["C9_HANDLER"]
    logging.info(f"Invoked - {handler_name}, {event}")

    zipfile = join(constants.EXE_PATH, handler_name + ".c9e")
    executable = c9e.load(zipfile, [constants.SRC_PATH, constants.LIB_PATH])

    args = [event, context]

    executor = LambdaExecutor(handler_name)
    controller = run_controller(
        executor,
        executable,
        args,
        timeout=os.environ["C9_TIMEOUT"] + 2,  # hackhackhack
        do_probe=True,
        # Other args...
    )
    if controller.finished:
        return controller.result
    else:
        return json.dumps(
            dict(
                session_id=event["session_id"],
                machine_id=event["machine_id"],
                finished=False,
            )
        )
