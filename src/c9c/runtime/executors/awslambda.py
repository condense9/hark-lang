import json

from ...lambda_utils import get_lambda_client


class LambdaRunner:
    def run(
        self, runner, executable_name, searchpath, session_id, machine_id, do_probe
    ):
        assert isinstance(runner, LambdaRunner)
        client = get_lambda_client()
        payload = dict(
            executable_name=executable_name,
            searchpath=searchpath,
            session_id=session_id,
            machine_id=machine_id,
            do_probe=do_probe,
        )
        res = client.invoke(
            # --
            FunctionName="c9run",
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        if res["StatusCode"] != 202 or "FunctionError" in res:
            err = res["Payload"].read()
            raise Exception(f"Invoke lambda failed {err}")
