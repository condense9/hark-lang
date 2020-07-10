"""Operate in your own cloud"""
import json
import logging

import botocore

from ..cloud import aws
from ..config import Config
from ..exceptions import UserResolvableError, UnexpectedError
from . import interface as ui
from .utils import make_python_layer_zip

LOG = logging.getLogger(__name__)


def _update_sp(prefix, sp):
    def update(resource):
        item = ui.dim(resource.__name__ + "...")
        sp.text = f"{prefix} {item}"

    return update


def deploy(args, config: Config):
    layer_zip = config.project.data_dir / "python_layer.zip"

    make_python_layer_zip(config, layer_zip)

    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid,
        instance=config.instance,
        source_layer_hash=aws.hash_file(layer_zip),
        source_layer_file=layer_zip,
    )

    spin_msg = "Deploying infrastructure"
    with ui.spin(spin_msg) as sp:
        # this is idempotent
        aws.deploy(deploy_config, callback_start=_update_sp(spin_msg, sp))
        sp.text = spin_msg + ui.dim(f" Build data: {config.project.data_dir}/")
        sp.ok(ui.TICK)

    with ui.spin("Checking API") as sp:
        api = aws.get_api()
        response = _call_cloud_api("version", {}, deploy_config)
        sp.text += " Teal " + ui.dim(response["version"])
        sp.ok(ui.TICK)

    with ui.spin(f"Deploying {config.project.teal_file}") as sp:
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

    spin_msg = "Destroying infrastructure"
    with ui.spin(spin_msg) as sp:
        aws.destroy(deploy_config, callback_start=_update_sp(spin_msg, sp))
        sp.text = spin_msg
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
            raise UserResolvableError(
                "AWS is not ready (KMSAccessDeniedException)",
                "Please try again in a few minutes, and let us know if it persists.",
            )
        raise

    LOG.info(logs)

    # This is when there's an unhandled exception in the Lambda.
    if "errorMessage" in response:
        msg = response["errorMessage"]
        if "Task timed out" in msg:
            raise UserResolvableError(msg, "Let us know if this persists.")
        raise UnexpectedError(msg + "\n" + "".join(response.get("stackTrace", "")))

    code = response.get("statusCode", None)
    if code == 400:
        # This is when there's a (handled) error.
        err = json.loads(response["body"])
        if "traceback" in err:
            raise UserResolvableError(
                err.get("message"), err.get("traceback", None),
            )
        else:
            raise UserResolvableError(err["message"], err["suggested_fix"])

    if code != 200:
        msg = f"Unexpected response code from AWS: {code}\n"
        raise UnexpectedError(msg + response)

    body = json.loads(response["body"]) if as_json else response["body"]
    LOG.info(body)

    return body
