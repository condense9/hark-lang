"""Operate in your own cloud"""
import json
import logging

import botocore

from ..cloud import aws
from ..config import Config
from . import interface as ui
from .utils import make_python_layer_zip

LOG = logging.getLogger(__name__)


def deploy(args, config: Config):
    layer_zip = config.project.data_dir / "python_layer.zip"

    make_python_layer_zip(config, layer_zip)

    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid,
        instance=config.instance,
        source_layer_hash=aws.hash_file(layer_zip),
        source_layer_file=layer_zip,
    )

    with ui.spin(args, "Deploying infrastructure") as sp:
        # this is idempotent
        aws.deploy(deploy_config)
        sp.text += ui.dim(f" {config.project.data_dir}/")
        sp.ok(ui.TICK)

    with ui.spin(args, "Checking API") as sp:
        api = aws.get_api()
        response = _call_cloud_api("version", {}, deploy_config)
        sp.text += " Teal " + ui.dim(response["version"])
        sp.ok(ui.TICK)

    with ui.spin(args, f"Deploying {config.project.teal_file}") as sp:
        # See teal_lang/executors/awslambda.py
        with open(config.project.teal_file) as f:
            content = f.read()
            payload = {"content": content}

        _call_cloud_api("set_exe", payload, deploy_config)
        sp.ok(ui.TICK)

    LOG.info(f"Uploaded {config.project.teal_file}")
    print(ui.good(f"\nDone. `teal invoke` to run main()."))


def destroy(args, config: Config):
    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid, instance=config.instance,
    )

    with ui.spin(args, "Destroying") as sp:
        aws.destroy(deploy_config)
        sp.ok(ui.TICK)

    print(ui.good(f"\nDone. You can safely `rm -rf {config.project.data_dir}`."))


def invoke(args, config: Config, payload: dict) -> dict:
    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid, instance=config.instance,
    )
    return _call_cloud_api("new", payload, deploy_config)


def stdout(args, config: Config, session_id: str) -> dict:
    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid, instance=config.instance,
    )
    return _call_cloud_api("get_output", {"session_id": session_id}, deploy_config)


def events(args, config: Config, session_id: str) -> dict:
    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid, instance=config.instance,
    )
    return _call_cloud_api("get_events", {"session_id": session_id}, deploy_config)


def logs(args, config: Config, session_id: str) -> dict:
    raise NotImplementedError


## Helpers:


def _call_cloud_api(function: str, args: dict, config: aws.DeployConfig, as_json=True):
    """Call a teal API endpoint and handle errors"""
    LOG.debug("Calling Teal cloud: %s %s", function, args)

    try:
        api = aws.get_api()
        logs, response = getattr(api, function).invoke(config, args)
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "KMSAccessDeniedException":
            msg = "\nAWS is not ready (KMSAccessDeniedException). Please try again in a few minutes."
            print(ui.bad(msg))
            ui.let_us_know("Invoke failed (KMSAccessDeniedException)")
            sys.exit(1)
        raise

    LOG.info(logs)

    # This is when there's an unhandled exception in the Lambda.
    if "errorMessage" in response:
        msg = response["errorMessage"]
        ui.exit_fail(msg, traceback=response.get("stackTrace", None))

    code = response.get("statusCode", None)
    if code == 400:
        # This is when there's a (handled) error
        err = json.loads(response["body"])
        ui.exit_fail(
            err.get("message", "StatusCode 400"), traceback=err.get("traceback", None)
        )

    if code != 200:
        print("\n")
        msg = f"Unexpected response code from AWS: {code}"
        ui.exit_fail(msg, data=response)

    body = json.loads(response["body"]) if as_json else response["body"]
    LOG.info(body)

    return body
