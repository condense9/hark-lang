"""AWS Lambda handlers for running and controller Teal"""
import functools
import json
import logging
import os
import sys
import time
import traceback

from .. import __version__, load
from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..exceptions import UserResolvableError
from ..executors.awslambda import Invoker
from ..machine.controller import ControllerError
from ..machine.machine import TlMachine
from ..teal_compiler.compiler import TealCompileError
from ..teal_parser.parser import TealParseError
from . import lambda_handlers

LOG = logging.getLogger(__name__)

# Get all logs into cloudwatch
logging.basicConfig(level=logging.WARNING)
root_logger = logging.getLogger("teal_lang")
root_logger.setLevel(level=logging.INFO)


# TODO structure return values and document. See cloud/api.py


def version(event, context):
    return _success(version=__version__)


def resume(event, context):
    """Handle the AWS lambda event for an existing session"""
    session_id = event["session_id"]
    vmid = int(event["vmid"])

    controller = ddb_controller.DataController.with_session_id(session_id)

    # Error handling is tricky in `resume`, because there's nothing to "return"
    # a result to. So all exceptions must appear in the AWS console.
    #
    # However, any waiting machines need to find out about this.
    _run_machine(controller, vmid)


def _run_machine(controller, vmid):
    try:
        invoker = Invoker(controller)
        machine = TlMachine(vmid, invoker)
        machine.run()

    # One of those rare times when we really do want to catch and record any
    # possible exception.
    except Exception as exc:
        state = controller.get_state(vmid)
        state.error_msg = "".join(traceback.format_exception(*sys.exc_info()))
        controller.set_state(vmid, state)
        controller.stop(vmid, finished_ok=False)
        raise


def event_handler(event, context):
    """Handle all 'events'.

    Events could be an S3 upload, an API trigger, ...
    """
    for h in lambda_handlers.ALL_HANDLERS:
        if h.can_handle(event):
            LOG.info("Handling with %s", str(h))
            return h.handle(event, _new_session, UserResolvableError)

    raise ValueError(f"Can't handle event {event}")


def set_exe(event, context):
    """Set the executable for the base session"""
    db.init_base_session()
    content = event["content"]

    try:
        exe = load.compile_text(content)
    except (TealCompileError, TealParseError) as exc:
        return _fail(f"Error compiling code.", suggested_fix=str(exc))

    db.set_base_exe(exe)
    return _success(message="Base Executable set successfully")


def getoutput(event, context):
    """Get Teal standard output for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return _fail("No session ID")

    try:
        controller = ddb_controller.DataController.with_session_id(session_id)
        output = [o.serialise() for o in controller.get_stdout()]
        errors = [
            controller.get_state(idx).error_msg for idx in controller.get_thread_ids()
        ]
    except ControllerError:
        return _fail("Error getting data")

    return _success(output=output, errors=errors)


def getevents(event, context) -> dict:
    """Get probe events for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return _fail("No session ID")

    try:
        controller = ddb_controller.DataController.with_session_id(session_id)
        events = [pe.serialise() for pe in controller.get_probe_events()]
    except ControllerError:
        return _fail("Error loading session data")

    return _success(events=events)


## Helpers


def _new_session(
    function, args, check_period, wait_for_finish, timeout, code_override=None
):
    """Create a new teal session"""
    LOG.info("Creating new session and running function: %s", function)
    controller = ddb_controller.DataController.with_new_session()

    if not code_override:
        exe = controller.executable
    else:
        # NOTE: First, teal code is loaded from the base executable. This allows
        # the user to override that with custom code. This might not be a good
        # idea...
        exe = load.compile_text(code_override)
        controller.set_executable(exe)

    if not exe:
        raise UserResolvableError("No Teal executable", "Run `teal deploy` first")

    try:
        fn_ptr = exe.bindings[function]
    except KeyError as exc:
        raise UserResolvableError(f"No such Teal function: `{function}`", "")

    try:
        vmid = controller.toplevel_machine(fn_ptr, args)
    except Exception as exc:
        # the exception message is lost because we may not even have a top level
        # machine. The controller should have an error property. TODO
        controller.broken = True
        msg = "".join(traceback.format_exception(*sys.exc_info()))
        raise UserResolvableError("Error initialising Teal", msg) from exc

    _run_machine(controller, vmid)

    # TODO reduce duplication - this is all similar to common.py
    if wait_for_finish:
        start_time = time.time()
        while not controller.all_stopped():
            time.sleep(check_period)
            if time.time() - start_time > timeout:
                raise UserResolvableError(
                    f"Timeout waiting for Teal program to finish ({controller.session_id})",
                    "",
                )

    return controller


def _success(code=200, **body_data):
    """Return successfully"""
    return {
        "teal_ok": True,
        **body_data,
    }


def _fail(msg, suggested_fix=""):
    """Return an error message"""
    extra = {}
    info = sys.exc_info()
    if info[0]:
        extra["traceback"] = "".join(traceback.format_exception(*info))

    return {
        # --
        "teal_ok": False,
        "message": msg,
        "suggested_fix": suggested_fix,
        **extra,
    }
