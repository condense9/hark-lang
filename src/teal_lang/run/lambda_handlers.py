"""Handle different kinds of events"""
import os
from abc import ABC, abstractmethod

from ..cli.main import TEAL_CLI_VERSION_KEY
from ..machine import types as mt


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
            return dict(
                teal_ok=False, message=str(exc), suggested_fix=exc.suggested_fix
            )

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
    """API Gateway (v2) HTTP endpoint handler"""

    @classmethod
    def can_handle(cls, event: dict):
        return "routeKey" in event and "rawPath" in event and "rawQueryString" in event

    @classmethod
    def handle(cls, event: dict, new_session, UserResolvableError) -> dict:
        controller = new_session(
            function="on_http",  # constant
            args=[mt.to_teal_type(event)],
            wait_for_finish=True,
            check_period=0.1,
            timeout=10.0,  # TODO? make configurable
        )

        return controller.get_top_level_result()


# List of all available handlers
ALL_HANDLERS = [CliHandler, S3Handler, HttpHandler]
