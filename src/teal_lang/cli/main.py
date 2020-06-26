"""Teal.

Usage:
  teal [options] info
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy [--config CONFIG]
  teal [options] destroy [--config CONFIG]
  teal [options] invoke [--config CONFIG] [ARG...]
  teal [options] events [--config CONFIG] [--unified | --json] [SESSION_ID]
  teal [options] logs [--config CONFIG] [SESSION_ID]
  teal [options] FILE [ARG...]
  teal --version
  teal --help

Commands:
  info     Show info about this Teal environment
  asm      Compile a file and print the bytecode listing.
  ast      Create a data flow graph (PNG).
  deploy   Deploy to the cloud.
  destroy  Remove cloud deployment.
  invoke   Invoke a teal function in the cloud.
  events   Get events for a session.
  logs     Get logs for a session.
  default  Run a Teal function locally.

Options:
  -h, --help      Show this screen.
  -q, --quiet     Be quiet.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --version       Show version.
  --no-colours    Disable colours in CLI output.

  -f FUNCTION, --fn=FUNCTION   Function to run      [default: main]
  -s MODE, --storage=MODE      memory | dynamodb    [default: memory]
  -c MODE, --concurrency=MODE  processes | threads  [default: threads]

  -o OUTPUT  Name of the output file

  --config CONFIG  Config file to use  [default: teal.toml]

  -u, --unified  Merge events into one table
  -j, --json     Print as json
"""

# http://try.docopt.org/
#
# - pyfiglet https://github.com/pwaller/pyfiglet
# - typer? https://typer.tiangolo.com/

import json
import logging
import subprocess
import sys
import time
from pathlib import Path

import botocore

from docopt import docopt

from .. import __version__
from ..config import load as load_config
from . import interface, utils
from .interface import (
    CROSS,
    TICK,
    bad,
    dim,
    exit_fail,
    good,
    init,
    neutral,
    primary,
    spin,
)

LOG = logging.getLogger(__name__)


def _run(args):
    cfg = load_config(config_file=Path(args["--config"]))
    fn = args["--fn"]
    filename = args["FILE"]
    sys.path.append(".")

    fn_args = args["ARG"]

    LOG.info(f"Running `{fn}` in {filename} ({len(fn_args)} args)...")

    if args["--storage"] == "memory":
        if args["--concurrency"] == "processes":
            exit_fail("Can't use processes with in-memory storage")

        from ..run.local import run_local

        # NOTE: we use the "lambda" timeout even for local invocations. Maybe
        # there should be a more general timeout
        result = run_local(filename, fn, fn_args, cfg.service.lambda_timeout)

    elif args["--storage"] == "dynamodb":
        from ..run.dynamodb import run_ddb_local, run_ddb_processes

        if args["--concurrency"] == "processes":
            result = run_ddb_processes(filename, fn, fn_args)
        else:
            result = run_ddb_local(filename, fn, fn_args)

    else:
        exit_fail("Bad storage type: " + str(args["--storage"]))

    if result:
        print(result)


def _ast(args):
    fn = args["--fn"]
    filename = Path(args["FILE"])

    if args["-o"]:
        dest_png = args["-o"]
    else:
        dest_png = f"{filename.stem}_{fn}.png"
    raise NotImplementedError


def _asm(args):
    from ..load import compile_file

    exe = compile_file(Path(args["FILE"]))
    print(neutral("\nBYTECODE:"))
    exe.listing()
    print(neutral("\nBINDINGS:\n"))
    exe.bindings_table()
    print()


def timed(fn):
    """Time execution of fn and print it"""

    def _wrapped(args, **kwargs):
        start = time.time()
        fn(args, **kwargs)
        end = time.time()
        if not args["--quiet"]:
            sys.stderr.write(str(dim(f"\n-- {int(end-start)}s\n")))

    return _wrapped


@timed
def _deploy(args):
    from ..cloud import aws

    cfg = load_config(
        config_file=Path(args["--config"]), require_dep_id=True, create_dep_id=True,
    )

    with spin(args, "Deploying infrastructure") as sp:
        # this is idempotent
        aws.deploy(cfg)
        sp.text += dim(f" {cfg.service.data_dir}/")
        sp.ok(TICK)

    with spin(args, "Checking API") as sp:
        api = aws.get_api()
        response = _call_cloud_api("version", {}, Path(args["--config"]))
        sp.text += " Teal " + dim(response["version"])
        sp.ok(TICK)

    with spin(args, "Deploying program") as sp:
        with open(cfg.service.teal_file) as f:
            content = f.read()

        # See teal_lang/executors/awslambda.py
        payload = {"content": content}
        _call_cloud_api("set_exe", payload, Path(args["--config"]))
        sp.ok(TICK)

    LOG.info(f"Uploaded {cfg.service.teal_file}")
    print(good(f"\nDone. `teal invoke` to run main()."))


@timed
def _destroy(args):
    from ..cloud import aws

    cfg = load_config(config_file=Path(args["--config"]), require_dep_id=True)

    with spin(args, "Destroying") as sp:
        aws.destroy(cfg)
        sp.ok(TICK)

    print(good(f"\nDone. You can safely `rm -rf {cfg.service.data_dir}`."))


def _call_cloud_api(function: str, args: dict, config_file: Path, as_json=True):
    """Call a teal API endpoint and handle errors"""
    from ..cloud import aws

    api = aws.get_api()
    cfg = load_config(config_file=config_file, require_dep_id=True)

    LOG.debug("Calling Teal cloud: %s %s", function, args)

    try:
        logs, response = getattr(api, function).invoke(cfg, args)
    except botocore.exceptions.ClientError as exc:
        if exc.response["Error"]["Code"] == "KMSAccessDeniedException":
            msg = "\nAWS is not ready (KMSAccessDeniedException). Please try again in a few minutes."
            print(bad(msg))
            interface.let_us_know("Deployment Failed (KMSAccessDeniedException)")
            sys.exit(1)
        raise

    LOG.info(logs)

    # This is when there's an unhandled exception in the Lambda.
    if "errorMessage" in response:
        print("\n" + bad("Unexpected exception!"))
        msg = response["errorMessage"]
        interface.let_us_know(msg)
        exit_fail(msg, response.get("stackTrace", None))

    code = response.get("statusCode", None)
    if code == 400:
        print("\n")
        # This is when there's a (handled) error
        err = json.loads(response["body"])
        exit_fail(err.get("message", "StatusCode 400"), err.get("traceback", None))

    if code != 200:
        print("\n")
        msg = f"Unexpected response code: {code}"
        interface.let_us_know(msg)
        exit_fail(msg)

    body = json.loads(response["body"]) if as_json else response["body"]
    LOG.info(body)

    return body


@timed
def _invoke(args):
    config_file = Path(args["--config"])
    cfg = load_config(config_file=config_file)
    function = args.get("--fn", "main")
    payload = {
        "function": function,
        "args": args["ARG"],
        "timeout": cfg.service.lambda_timeout - 3,  # FIXME
    }

    with spin(args, str(primary(f"{function}(...)"))) as sp:
        data = _call_cloud_api("new", payload, config_file)
        sp.text += " " + dim(data["session_id"])

        if data["broken"]:
            sp.fail(CROSS)
        else:
            sp.ok(TICK)

    utils.save_last_session_id(cfg, data["session_id"])

    with spin(args, "Getting logs") as sp:
        logs = _call_cloud_api(
            "get_output", {"session_id": data["session_id"]}, config_file
        )
        sp.ok(TICK)

    interface.print_outputs(logs)

    if data["finished"]:
        if not args["--quiet"]:
            print(dim("\n=>"))
        print(data["result"])


@timed
def _events(args):
    session_id = utils.get_session_id(args)

    if args["--json"]:
        # Don't show the spinner in JSON mode
        data = _call_cloud_api(
            "get_events", {"session_id": session_id}, Path(args["--config"]),
        )
        print(json.dumps(data, indent=2))
    else:
        with spin(args, f"Getting events"):
            data = _call_cloud_api(
                "get_events", {"session_id": session_id}, Path(args["--config"]),
            )
        if args["--unified"]:
            interface.print_events_unified(data)
        else:
            interface.print_events_by_machine(data)


@timed
def _logs(args):
    session_id = utils.get_session_id(args)

    with spin(args, f"Getting output {dim(session_id)}") as sp:
        data = _call_cloud_api(
            "get_output", {"session_id": session_id}, Path(args["--config"]),
        )
        sp.ok(TICK)
    if not args["--quiet"]:
        print("")
    interface.print_outputs(data)


@timed
def _info(args):
    # API URL
    # deployment ID
    # deployed teal version
    # last session ID
    # links to console items?
    raise NotImplementedError


def main():
    args = docopt(__doc__, version=__version__)
    init(args)
    LOG.debug("CLI args: %s", args)
    if not args["--quiet"]:
        print("")  # Space in the CLI

    if args["ast"]:
        _ast(args)
    elif args["info"]:
        _info(args)
    elif args["asm"]:
        _asm(args)
    elif args["deploy"]:
        _deploy(args)
    elif args["destroy"]:
        _destroy(args)
    elif args["invoke"]:
        _invoke(args)
    elif args["events"]:
        _events(args)
    elif args["logs"]:
        _logs(args)
    elif args["FILE"] and args["FILE"].endswith(".tl"):
        _run(args)
    else:
        print(bad("Invalid command line.\n"))
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
