"""Handle different kinds of events"""
from abc import ABC, abstractmethod

from ..machine import types as mt
from ..cli.main import TEAL_CLI_VERSION_KEY


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
    def get_invoke_args(cls, event: dict) -> dict:
        """Get arguments to start a new session which handles the event.

        Internally, the dict is passed to aws._new_session.
        """


## Concrete Implementations


class CliHandler(TealEventHandler):
    """Handle invocations by the Teal CLI"""

    @classmethod
    def can_handle(cls, event: dict):
        return TEAL_CLI_VERSION_KEY in event

    @classmethod
    def get_invoke_args(cls, event: dict) -> dict:
        try:
            timeout = int(event["timeout"])
        except KeyError:
            timeout = int(os.getenv("FIXED_TEAL_TIMEOUT", 5))

        return dict(
            function=event.get("function", "main"),
            args=[mt.TlString(a) for a in event.get("args", [])],
            check_period=event.get("check_period", 1),
            wait_for_finish=event.get("wait_for_finish", True),
            timeout=timeout,
            code_override=event.get("code", None),
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
    def get_invoke_args(cls, event: dict) -> dict:
        """Get arguments to invoke the upload handler

        NOTE: does not wait for the session to finish!
        """
        data = event["Records"][0]["s3"]

        bucket = data["bucket"]["name"]
        key = data["object"]["key"]  # NOTE - could check size here

        return dict(
            function="on_upload",  # constant
            args=[mt.TlString(bucket), mt.TlString(key), mt.TlString("aws")],
            wait_for_finish=False,
            check_period=None,
            timeout=None,
        )


class ApiHandler(TealEventHandler):
    @classmethod
    def can_handle(cls, event: dict):
        return "routeKey" in event and "rawPath" in event and "rawQueryString" in event

    @classmethod
    def get_invoke_args(cls, event: dict) -> dict:
        path = event["rawPath"]
        query = event["rawQueryString"]

        return dict(
            function="on_apicall",  # constant
            args=[mt.TlString(path), mt.TlString(query), mt.TlString("aws")],
            wait_for_finish=True,
            check_period=0.02,
            timeout=3.0,  # TODO? make configurable
        )


# List of all available handlers
ALL_HANDLERS = [CliHandler, S3Handler, ApiHandler]
