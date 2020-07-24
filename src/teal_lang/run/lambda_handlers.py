"""Handle different kinds of events"""
import json
import logging
import os
from abc import ABC, abstractmethod

from ..machine import types as mt

TEAL_CLI_VERSION_KEY = "teal_ver"

LOG = logging.getLogger(__name__)


class TealEventHandler(ABC):
    """An event handler.

    Designed so new event handlers can be built without having to interface
    tightly with Teal

    """

    @classmethod
    @abstractmethod
    def can_handle(cls, event: dict) -> bool:
        """Return whether event can be handled by this class."""

    @classmethod
    @abstractmethod
    def handle(cls, event: dict, new_session, UserResolvableError) -> dict:
        """Handle an event"""


## Concrete Implementations


class CliHandler(TealEventHandler):
    """Handle invocations by the Teal CLI"""

    @classmethod
    def can_handle(cls, event: dict):
        return TEAL_CLI_VERSION_KEY in event

    @classmethod
    def handle(cls, event: dict, new_session, UserResolvableError) -> dict:
        try:
            timeout = int(event["timeout"])
        except KeyError:
            timeout = int(os.getenv("FIXED_TEAL_TIMEOUT", 5))

        try:
            controller = new_session(
                function=event.get("function", "main"),
                args=[mt.TlString(a) for a in event.get("args", [])],
                check_period=event.get("check_period", 0.2),
                wait_for_finish=event.get("wait_for_finish", True),
                timeout=timeout,
                code_override=event.get("code", None),
            )
        except UserResolvableError as exc:
            return dict(teal_ok=False, message=exc.msg, suggested_fix=exc.suggested_fix)

        # The "teal_ok" element is required (see in_own.py)
        return dict(
            teal_ok=True,
            session_id=controller.session_id,
            finished=controller.all_stopped(),
            broken=controller.broken,
            result=controller.get_top_level_result(),
        )


class S3Handler(TealEventHandler):
    """Handle S3 upload events"""

    @classmethod
    def can_handle(cls, event: dict):
        return (
            "Records" in event
            and len(event["Records"]) > 0
            and "eventSource" in event["Records"][0]
            and event["Records"][0]["eventSource"] == "aws:s3"
            and event["Records"][0]["s3"]["s3SchemaVersion"] == "1.0"
        )

    @classmethod
    def handle(cls, event: dict, new_session, UserResolvableError) -> dict:
        """Get arguments to invoke the upload handler

        NOTE: does not wait for the session to finish! All exceptions must end
        up in the machine state.

        """
        data = event["Records"][0]["s3"]

        bucket = data["bucket"]["name"]
        key = data["object"]["key"]  # NOTE - could check size here

        new_session(
            function="on_upload",  # constant
            args=[mt.TlString(bucket), mt.TlString(key)],
            wait_for_finish=False,
            check_period=None,
            timeout=None,
        )


class HttpHandler(TealEventHandler):
    """API Gateway (v1) HTTP endpoint handler"""

    @classmethod
    def can_handle(cls, event: dict):
        return (
            "httpMethod" in event and "path" in event and event.get("version") == "1.0"
        )

    @classmethod
    def handle(cls, event: dict, new_session, UserResolvableError) -> dict:
        method = event["httpMethod"]
        path = event["path"]

        controller = new_session(
            function="on_http",  # constant
            args=[mt.to_teal_type(o) for o in (method, path, event)],
            wait_for_finish=False,
            check_period=0.1,
            timeout=10.0,  # TODO? make configurable
        )

        result = controller.get_top_level_result()
        LOG.info(f"Finished HTTP handling. Result: {result}")

        # Indicate an internal server error to the client
        if controller.broken:
            raise Exception("Controller broken")

        # Try to DWIM: return a dict to do everything yourself, or return a
        # string to have this handler do something sensible with it.
        # TODO: HTML detection

        if isinstance(result, dict) and "statusCode" in result:
            return result

        if isinstance(result, dict):
            ct = "application/json"
            body = json.dumps(result)
        else:
            ct = "text/plain"
            body = str(result)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": ct},
            "isBase64Encoded": False,
            "body": body,
        }


# List of all available handlers
ALL_HANDLERS = [CliHandler, S3Handler, HttpHandler]
