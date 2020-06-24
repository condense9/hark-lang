"""Teal.

Usage:
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy [--config CONFIG]
  teal [options] destroy [--config CONFIG]
  teal [options] invoke [--config CONFIG] [ARG...]
  teal [options] events [--config CONFIG] [--unified | --json] SESSION_ID
  teal [options] logs [--config CONFIG] SESSION_ID
  teal [options] FILE [ARG...]
  teal --version
  teal --help

Commands:
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

from docopt import docopt
from yaspin import yaspin
from yaspin.spinners import Spinners

from .. import __version__
from . import interface
from .interface import good, bad, neutral, dim, init, TICK, CROSS, primary, exit_fail

LOG = logging.getLogger(__name__)


def _run(args):
    from ..config import load

    cfg = load(config_file=Path(args["--config"]))
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
    from .. import load

    exe = load.compile_file(Path(args["FILE"]))
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
            sys.stderr.write(str(dim(f"\n-- {int(end-start)}s elapsed.\n")))

    return _wrapped


@timed
def _deploy(args):
    from ..cloud import aws
    from ..config import load
    import botocore

    cfg = load(
        config_file=Path(args["--config"]), require_dep_id=True, create_dep_id=True,
    )

    with yaspin(Spinners.dots, text="Deploying infrastructure") as sp:
        # this is idempotent
        aws.deploy(cfg)
        sp.text += dim(f" {cfg.service.data_dir}/")
        sp.ok(TICK)

    with yaspin(Spinners.dots, text="Checking version") as sp:
        api = aws.get_api()

        try:
            response = _call_cloud_api("version", {}, Path(args["--config"]))
        except botocore.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] == "KMSAccessDeniedException":
                print(
                    bad("AWS is not ready. Try `teal deploy` again in a few minutes.")
                )
                interface.let_us_know()
                sys.exit(1)
            raise

        sp.text += " " + dim(response["version"])
        sp.ok(TICK)

    with yaspin(Spinners.dots, text="Deploying program") as sp:
        with open(cfg.service.teal_file) as f:
            content = f.read()

        # See teal_lang/executors/awslambda.py
        exe_payload = {"content": content}
        logs, response = api.set_exe.invoke(cfg, exe_payload)
        sp.ok(TICK)

    LOG.info(f"Uploaded {cfg.service.teal_file}")
    print(good(f"\nDone. `teal invoke` to run main()."))


@timed
def _destroy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load(config_file=Path(args["--config"]), require_dep_id=True)

    with yaspin(Spinners.dots, text="Destroying") as sp:
        aws.destroy(cfg)
        sp.ok(TICK)

    print(good(f"Done. You can safely `rm -rf {cfg.service.data_dir}`."))


def _call_cloud_api(function: str, args: dict, config_file: Path, as_json=True):
    """Call a teal API endpoint and handle errors"""
    from ..cloud import aws
    from ..config import load

    api = aws.get_api()
    cfg = load(config_file=config_file, require_dep_id=True)

    # See teal_lang/executors/awslambda.py
    LOG.debug("Calling Teal cloud: %s %s", function, args)
    logs, response = getattr(api, function).invoke(cfg, args)
    LOG.info(logs)

    # This is when there's an unhandled exception in the Lambda.
    if "errorMessage" in response:
        msg = (
            "Teal Bug! Please report this! "
            + "https://github.com/condense9/teal-lang/issues/new \n\n"
            + response["errorMessage"]
        )
        exit_fail(msg, response.get("stackTrace", None))

    code = response.get("statusCode", None)
    if code == 400:
        # This is when there's a (handled) error
        err = json.loads(response["body"])
        exit_fail(err.get("message", "StatusCode 400"))

    if code != 200:
        exit_fail(f"Unexpected response code: {code}")

    body = json.loads(response["body"]) if as_json else response["body"]
    LOG.info(body)

    return body


@timed
def _invoke(args):
    from ..config import load

    config_file = Path(args["--config"])
    cfg = load(config_file=config_file)
    function = args.get("--fn", "main")
    payload = {
        "function": function,
        "args": args["ARG"],
        "timeout": cfg.service.lambda_timeout - 3,  # FIXME
    }
    with yaspin(Spinners.dots, text=f"Invoking {primary(function)}") as sp:
        data = _call_cloud_api("new", payload, config_file)
        sp.text += " " + dim(data["session_id"])

        if data["broken"]:
            sp.fail(CROSS)
        else:
            sp.ok(TICK)

    session_id = data["session_id"]
    last_session_file = cfg.service.data_dir / "last_session_id.txt"
    with open(last_session_file, "w") as f:
        f.write(session_id)
        LOG.info("Session ID: %s (saved in %s)", session_id, last_session_file)

    if data["broken"]:
        with yaspin(Spinners.dots, text=f"Getting logs"):
            logs = _call_cloud_api(
                "get_output", {"session_id": session_id}, config_file
            )

        interface.print_outputs(logs)

    elif data["finished"]:
        print("\n" + str(data["result"]))


@timed
def _events(args):
    if args["--json"]:
        # Don't show the spinner in JSON mode
        data = _call_cloud_api(
            "get_events", {"session_id": args["SESSION_ID"]}, Path(args["--config"]),
        )
        print(json.dumps(data, indent=2))
    else:
        with yaspin(Spinners.dots, text=f"Getting events"):
            data = _call_cloud_api(
                "get_events",
                {"session_id": args["SESSION_ID"]},
                Path(args["--config"]),
            )
        if args["--unified"]:
            interface.print_events_unified(data)
        else:
            interface.print_events_by_machine(data)


@timed
def _logs(args):
    from . import interface

    with yaspin(Spinners.dots, text=f"Getting logs"):
        data = _call_cloud_api(
            "get_output", {"session_id": args["SESSION_ID"]}, Path(args["--config"]),
        )
    interface.print_outputs(data)


def main():
    args = docopt(__doc__, version=__version__)
    init(args)
    LOG.debug("CLI args: %s", args)
    print("")  # Space in the CLI

    if args["ast"]:
        _ast(args)
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
