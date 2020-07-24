"""The HTTP API interface to a Teal Instance"""

import logging
from pathlib import Path
from typing import List, Any
from dataclasses import dataclass

import botocore

from .. import __version__
from ..exceptions import UnexpectedError, UserResolvableError
from . import aws
from .aws import FnVersion, FnSetexe, FnEventHandler, FnGetEvents, FnGetOutput
from ..run.lambda_handlers import TEAL_CLI_VERSION_KEY
from ..config import Config

# TODO structure return values. See run/aws.py

LOG = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    session_id: str
    broken: bool
    finished: bool
    result: Any


class TealInstanceApi:
    """Functional interface to a remote teal instance"""

    def __init__(self, config: Config, hosted_instance_state=None):
        self.config = config
        self.hosted_instance_state = hosted_instance_state
        self._deploy_config = aws.DeployConfig(
            uuid=config.instance_uuid, instance=config.instance,
        )

    def version(self) -> str:
        """Get the version of the instance"""
        data = _call_cloud_api(self._deploy_config, FnVersion, {})
        return data["version"]

    def set_exe(self, teal_source: str):
        """Set the base (default) executable"""
        data = _call_cloud_api(self._deploy_config, FnSetexe, {"content": teal_source})
        if data.get("message") != "Base Executable set successfully":
            raise UnexpectedError("set_exe returned an unexpected result")

    def invoke(
        self, function: str, args: List[str], timeout, wait_for_finish
    ) -> SessionInfo:
        """Invoke (call) a Teal function"""
        payload = {
            TEAL_CLI_VERSION_KEY: __version__,
            "function": function,
            "args": args,
            "timeout": timeout,
            "wait_for_finish": wait_for_finish,
        }
        data = _call_cloud_api(self._deploy_config, FnEventHandler, payload)
        return SessionInfo(**data)

    def get_stdout(self, session_id: str) -> dict:
        # TODO structure this result
        return _call_cloud_api(
            self._deploy_config, FnGetOutput, {"session_id": session_id}
        )

    def get_events(self, session_id: str):
        # TODO structure this result
        return _call_cloud_api(
            self._deploy_config, FnGetEvents, {"session_id": session_id}
        )

    def get_logs(self, session_id: str):
        raise NotImplementedError

    def upload_file(self, s3_url: str, filepath: Path):
        """Upload a file to the instance object store"""
        LOG.info(f"Uploading {filepath} to {s3_url}")
        client = aws.get_client("s3")
        bucket, key = aws.get_bucket_and_key(s3_url)
        aws.upload_if_necessary(client, bucket, key, filepath)


def _call_cloud_api(
    config: aws.DeployConfig, cls: aws.TealFunction, args: dict, as_json=True
):
    """Call an instance control function and handle errors"""
    LOG.info("Calling Teal cloud: %s %s", cls.__name__, args)

    try:
        logs, response = cls.invoke(config, args)
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "KMSAccessDeniedException":
            raise UserResolvableError(
                "AWS is not ready (KMSAccessDeniedException)",
                "Please try again in a few minutes, and let us know if it persists.",
            )
        raise

    LOG.info(response)
    LOG.info(logs)

    # This is when there's an unhandled exception in the Lambda.
    if "errorMessage" in response:
        msg = response["errorMessage"]
        if "Task timed out" in msg:
            raise UserResolvableError(msg, "Let us know if this persists.")
        raise UnexpectedError(msg + "\n" + "".join(response.get("stackTrace", "")))

    if "errorType" in response:
        raise UnexpectedError(
            response["errorType"] + "\n" + "".join(response.get("stackTrace", ""))
        )

    if not response["teal_ok"]:
        # This is when there's a (handled) error. See lambda_handlers.py
        LOG.info("teal_ok False in response - something broke while running Teal")
        if "traceback" in response:
            raise UserResolvableError(
                response.get("message"), response.get("traceback", None),
            )
        else:
            raise UserResolvableError(response["message"], response["suggested_fix"])

    response.pop("teal_ok")
    return response
