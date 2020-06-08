import functools
import json
import logging
import os
import sys
import time
import traceback
from typing import List

import boto3
import botocore

from operator import itemgetter

from .. import __version__, load
from ..cli.styling import dim, em
from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..machine import TlMachine
from ..machine import types as mt
from ..machine.executable import Executable

RESUME_FN_NAME = os.environ.get("RESUME_FN_NAME", "resume")

LOG = logging.getLogger(__name__)

if os.environ.get("ENABLE_LOGGING", False):
    logging.basicConfig(level=logging.INFO)


def get_lambda_client():
    region = os.environ.get("TL_REGION", None)

    return boto3.client(
        "lambda",
        region_name=region,
        config=botocore.config.Config(retries={"max_attempts": 0}),
    )


class Invoker:
    def __init__(self, data_controller):
        self.data_controller = data_controller
        self.resume_fn_name = RESUME_FN_NAME
        self.exception = None

    def invoke(self, vmid, run_async=True):
        client = get_lambda_client()
        event = dict(
            # --
            session_id=self.data_controller.session.session_id,
            vmid=vmid,
        )
        res = client.invoke(
            # --
            FunctionName=self.resume_fn_name,
            InvocationType="Event",
            Payload=json.dumps(event),
        )
        if res["StatusCode"] != 202 or "FunctionError" in res:
            err = res["Payload"].read()
            # TODO retry!
            raise Exception(f"Invoke lambda {self.resume_fn_name} failed {err}")


# These are Lambda handlers, and maybe should be somewhere else:


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


def try_run(session, vmid, invoker):
    """Try to run a machine, saving a session exception if it fails"""
    machine = TlMachine(vmid, invoker)
    try:
        machine.run()
    except Exception as exc:
        session.refresh()
        session.machines[vmid].exception = traceback.format_exc()
        session.save()
        raise


def resume(event, context):
    """Handle the AWS lambda event for an existing session"""
    session_id = event["session_id"]
    vmid = event["vmid"]

    session = db.Session.get(session_id)
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = Invoker(controller)

    try_run(session, vmid, invoker)

    return success(
        session_id=session_id,
        vmid=vmid,
        finished=controller.finished,
        result=controller.result,
    )


def new(event, context):
    """Create a new session - event is a simple payload"""
    function = event.get("function", "main")
    args = [mt.TlString(a) for a in event.get("args", [])]
    check_period = event.get("check_period", 1)
    wait_for_finish = event.get("wait_for_finish", True)
    code = event.get("code", None)
    timeout = event.get("timeout", None)
    timeout = timeout if timeout else int(os.getenv("FIXED_TEAL_TIMEOUT", 5))

    session = db.new_session()

    if not code:
        exe = Executable.deserialise(session.executable)

    # NOTE: First, teal code is loaded from the base executable. This allows the
    # user to override that with custom code. This might not be a good idea...
    else:
        try:
            exe = load.compile_text(code)
        except Exception as exc:
            return fail(f"Error compiling code:\n{exc}")

        try:
            session.executable = exe.serialise()
            session.save()
            LOG.info("Set session code")
        except db.Session.UpdateError:
            return fail("Error saving code")

    try:
        lock = db.SessionLocker(session)
        controller = ddb_controller.DataController(session, lock)
        invoker = Invoker(controller)
        fn_ptr = exe.bindings[function]
        vmid = controller.new_machine(args, fn_ptr, is_top_level=True)
    except Exception as exc:
        return fail("Error initialising", exception=exc)

    try_run(session, vmid, invoker)

    if wait_for_finish:
        start_time = time.time()
        while not controller.finished:
            time.sleep(check_period)
            if time.time() - start_time > timeout:
                return fail("Timeout waiting for finish", session_id=session.session_id)

    return success(
        session_id=session.session_id,
        vmid=vmid,
        finished=controller.finished,
        result=controller.result,
    )


def set_exe(event, context):
    """Set the executable for the base session"""
    db.init_base_session()
    content = event["content"]
    exe = load.compile_text(content)
    db.set_base_exe(exe)
    return success(
        # --
        message="Base Executable set successfully"
    )


def set_session_exe(event, context):
    """Set the executable for the specified session session"""
    session_id = event.get("session_id", None)
    content = event.get("content", None)

    if not content:
        return fail("No Teal code")

    if not session_id:
        return fail("No session ID")

    try:
        session = db.Session.get(session_id)
    except db.Session.DoesNotExist:
        return fail("Couldn't find that session")

    try:
        exe = load.compile_text(content)
    except:
        return fail("Error compiling code")

    try:
        session.executable = exe.serialise()
        session.save()
    except db.Session.UpdateError:
        return fail("Error saving code")

    return success(message="Executable set successfully")


def getoutput(event, context):
    """Get Teal standard output for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return fail("No session ID")

    try:
        session = db.Session.get(session_id)
    except db.Session.DoesNotExist:
        return fail("Couldn't find that session")

    output = session.stdout
    exceptions = [m.exception for m in session.machines]

    return success(output=output, exceptions=exceptions)


def getevents(event, context) -> dict:
    """Get probe events for a session"""
    session_id = event.get("session_id", None)

    if not session_id:
        return fail("No session ID")

    try:
        session = db.Session.get(session_id)
    except db.Session.DoesNotExist:
        return fail("Couldn't find that session")

    events = [[pe.as_dict() for pe in m.probe_events] for m in session.machines]

    return success(events=events)


## CLI helpers (TODO - these probably shouldn't be here):


def print_outputs(success_result: dict):
    exceptions = success_result["exceptions"]
    output = success_result["output"]

    print("".join(output))
    for idx, item in enumerate(exceptions):
        if item:
            print(em(f"Exception in Thread {idx}!"))
            print(item)


def print_events_by_machine(success_result: dict):
    """Print the results of `getevents`, grouped by machine"""
    elist = success_result["events"]
    lowest_time = min(float(event["time"]) for machines in elist for event in machines)

    for i, machine in enumerate(elist):
        print(em(f"Thread {i}:"))
        for event in machine:
            offset_time = float(event["time"]) - lowest_time
            time = dim("{:.3f}".format(offset_time))
            name = event["event"]
            data = event["data"] if len(event["data"]) else ""
            print(f"{time}  {name} {data}")


def print_events_unified(success_result: dict):
    """Print the results of `getevents`, in one table"""
    elist = success_result["events"]
    lowest_time = min(float(event["time"]) for machines in elist for event in machines)

    all_events = []
    for i, machine in enumerate(elist):
        for event in machine:
            offset_time = float(event["time"]) - lowest_time
            event["machine"] = i
            event["offset_time"] = offset_time
            event["insert_idx"] = len(all_events)
            all_events.append(event)

    print(em("{:>8}  {}  {}".format("Time", "Thread", "Event")))
    for event in sorted(all_events, key=itemgetter("offset_time", "insert_idx")):
        time = dim("{:8.3f}".format(event["offset_time"]))
        name = event["event"]
        machine = event["machine"]
        data = event["data"] if len(event["data"]) else ""
        print(f"{time:^}  {machine:^7}  {name} {data}")


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
