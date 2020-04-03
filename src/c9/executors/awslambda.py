import json
import logging
from os.path import join

from .. import packer
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
def handler(run_controller, event, context):
    """Handle the AWS lambda event for an existing session, returning a JSON response"""
    logging.info(f"Invoked - {event}")

    exe_path = packer.EXE_PATH
    src_path = packer.SRC_PATH
    zipfile = join(exe_path, event["executable_name"] + ".c9e")
    executable = c9e.load(zipfile, [src_path])

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
