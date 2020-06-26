"""AWS Lambda handlers for running and controller Teal"""
import functools
import json
import sys
import os
import time
import traceback

from .. import __version__, load
from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..executors.awslambda import Invoker
from ..machine import TlMachine
from ..machine import types as mt
from ..machine.controller import ControllerError
from ..machine.executable import Executable
from ..teal_compiler.compiler import CompileError
from ..teal_parser.parser import TealSyntaxError

from . import lambda_handlers


def version(event, context):
    return success(version=__version__)


def success(code=200, **body_data):
    """Return successfully"""
    return dict(
        statusCode=code,
        isBase64Encoded=False,
        # https://www.serverless.com/blog/cors-api-gateway-survival-guide/
        headers={
            "Access-Control-Allow-Origin": "*",  # Required for CORS
            "Access-Control-Allow-Credentials": True,
        },
        body=json.dumps(body_data),
    )


def fail(msg, code=400, exception=None, **body_data):
    """Return an error message"""
    # 400 = client error
    # 500 = server error
    if exception:
        etype, value, tb = sys.exc_info()
        body_data["etype"] = str(etype)
        body_data["evalue"] = str(value)
        body_data["traceback"] = traceback.format_exception(etype, value, tb)

    return dict(
        statusCode=code,
        isBase64Encoded=False,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        body=json.dumps({"message": msg, **body_data}),
    )


def resume(event, context):
    """Handle the AWS lambda event for an existing session"""
    session_id = event["session_id"]
    vmid = int(event["vmid"])

    controller = ddb_controller.DataController.with_session_id(session_id)

    # Error handling is trick in `resume`, because there's nothing to "return" a
    # result to. So all exceptions must appear in the AWS console.
    #
    # However, any waiting machines need to find out about this.

    try:
        invoker = Invoker(controller)
        machine = TlMachine(vmid, invoker)
        machine.run()
    except Exception as exc:
        state = controller.get_state(vmid)
        state.error_msg = "".join(traceback.format_exception(*sys.exc_info()))
        controller.set_state(vmid, state)
        controller.stop(vmid, finished_ok=False)
        raise


def new(event, context):
    """Create a new session - event is a simple payload"""
    timeout = event.get("timeout", None)

    return _new_session(
        function=event.get("function", "main"),
        args=[mt.TlString(a) for a in event.get("args", [])],
        check_period=event.get("check_period", 1),
        wait_for_finish=event.get("wait_for_finish", True),
        timeout=timeout if timeout else int(os.getenv("FIXED_TEAL_TIMEOUT", 5)),
        code_override=event.get("code", None),
    )


def event_handler(event, context):
    """Handle all 'events'.

    Events could be an S3 upload, an API trigger, ...
    """
    for h in lambda_handlers.ALL_HANDLERS:
        if h.can_handle(event):
            return _new_session(**h.get_invoke_args(event))

    raise Exception(f"Can't handle event {event}")


def set_exe(event, context):
    """Set the executable for the base session"""
    db.init_base_session()
    content = event["content"]

    try:
        exe = load.compile_text(content)
    except Exception as exc:
        return fail(f"Error compiling code", exception=exc)

    db.set_base_exe(exe)
    return success(message="Base Executable set successfully")


def getoutput(event, context):
    """Get Teal standard output for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return fail("No session ID")

    try:
        controller = ddb_controller.DataController.with_session_id(session_id)
        output = [o.serialise() for o in controller.get_stdout()]
        errors = [
            controller.get_state(idx).error_msg for idx in controller.get_thread_ids()
        ]
    except ControllerError as exc:
        return fail("Error getting data", exception=exc)

    return success(output=output, errors=errors)


def getevents(event, context) -> dict:
    """Get probe events for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return fail("No session ID")

    try:
        controller = ddb_controller.DataController.with_session_id(session_id)
        events = [pe.serialise() for pe in controller.get_probe_events()]
    except ControllerError as exc:
        return fail("Error loading session data", exception=exc)

    return success(events=events)


## API gateway wrappers


def wrap_apigw(fn):
    """API Gateway wrapper for FN"""

    @functools.wraps(fn)
    def _wrapper(event, context):
        try:
            body = json.loads(event["body"])
        except (KeyError, TypeError, json.decoder.JSONDecodeError):
            return fail("No event body")

        return fn(body, context)

    return _wrapper


new_apigw = wrap_apigw(new)
getoutput_apigw = wrap_apigw(getoutput)
getevents_apigw = wrap_apigw(getevents)
version_apigw = wrap_apigw(version)


##


def _new_session(
    function, args, check_period, wait_for_finish, timeout, code_override=None
):
    """Create a new teal session"""
    controller = ddb_controller.DataController.with_new_session()

    if not code_override:
        exe = controller.executable

    # NOTE: First, teal code is loaded from the base executable. This allows the
    # user to override that with custom code. This might not be a good idea...
    else:
        try:
            exe = load.compile_text(code_override)
        except (TealSyntaxError, CompileError) as exc:
            # TODO use load.msg to print this nicely
            return fail(f"Code error", exception=exc)
        except Exception as exc:
            return fail(f"Teal bug:", exception=exc)

        try:
            controller.set_executable(exe)
        except ddb_controller.ControllerError as exc:
            return fail("Error saving code:", exception=exc)

    try:
        fn_ptr = exe.bindings[function]
    except KeyError as exc:
        return fail(f"No such Teal function: `{function}`")

    try:
        invoker = Invoker(controller)
        vmid = controller.toplevel_machine(fn_ptr, args)
        machine = TlMachine(vmid, invoker)
    except Exception as exc:
        try:
            controller.broken = True
        except ControllerError:
            pass
        return fail("Error initialising Teal:", exception=exc)

    machine.run()

    # TODO reduce duplication - this is all similar to common.py
    if wait_for_finish:
        start_time = time.time()
        while not controller.all_stopped():
            time.sleep(check_period)
            if time.time() - start_time > timeout:
                return fail(
                    "Timeout waiting for Teal program to finish",
                    session_id=controller.session_id,
                )

    return success(
        session_id=controller.session_id,
        vmid=vmid,
        finished=controller.all_stopped(),
        broken=controller.broken,
        result=controller.result,
    )
