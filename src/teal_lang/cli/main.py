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
# - colorama https://pypi.org/project/colorama/

import logging
import sys
from pathlib import Path
import subprocess

import time
import pprint
import json
import colorama

from .. import __version__
from .styling import em, dim

from docopt import docopt

LOG = logging.getLogger(__name__)


def _run(args):
    fn = args["--fn"]
    filename = args["FILE"]
    sys.path.append(".")

    fn_args = args["ARG"]

    LOG.info(f"Running `{fn}` in {filename} ({len(fn_args)} args)...")

    if args["--storage"] == "memory":
        if args["--concurrency"] == "processes":
            raise ValueError("Can't use processes with in-memory storage")

        from ..run.local import run_local

        run_local(filename, fn, fn_args)

    elif args["--storage"] == "dynamodb":
        from ..run.dynamodb import run_ddb_local, run_ddb_processes

        if args["--concurrency"] == "processes":
            run_ddb_processes(filename, fn, fn_args)
        else:
            run_ddb_local(filename, fn, fn_args)

    else:
        raise ValueError(args["--storage"])


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
    print(em("\nBYTECODE:"))
    print(exe.listing())
    print(em("\nBINDINGS:\n"))
    print(exe.bindings_table())
    print()


def timed(fn):
    """Time execution of fn and print it"""

    def _wrapped(args, **kwargs):
        start = time.time()
        fn(args, **kwargs)
        end = time.time()
        if not args["--quiet"]:
            print(f"Done ({int(end-start)}s elapsed).")

    return _wrapped


@timed
def _deploy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load(config_file=Path(args["--config"]), create_deployment_id=True)

    # Deploy the infrastructure (idempotent)
    aws.deploy(cfg)
    api = aws.get_api()

    logs, response = api.version.invoke(cfg, {})
    print("Teal:", response["body"])

    # Deploy the teal code
    with open(cfg.service.teal_file) as f:
        content = f.read()

    # See teal_lang/executors/awslambda.py
    exe_payload = {"content": content}
    logs, response = api.set_exe.invoke(cfg, exe_payload)
    LOG.info(f"Uploaded {cfg.service.teal_file}")


@timed
def _destroy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load(config_file=Path(args["--config"]))
    aws.destroy(cfg)


class InvokeError(Exception):
    """Something broke while running"""

    def __init__(self, err, traceback=None):
        self.err = err
        self.traceback = traceback

    def __str__(self):
        res = "\n\n" + str(self.err)
        if self.traceback:
            res += "\n" + "".join(self.traceback)
        return res


def _call_cloud_api(function, args, config_file, verbose=False, as_json=True):
    from ..cloud import aws
    from ..config import load

    api = aws.get_api()
    cfg = load(config_file=config_file)

    # See teal_lang/executors/awslambda.py
    logs, response = getattr(api, function).invoke(cfg, args)
    if verbose:
        print(logs)

    if "errorMessage" in response:
        raise InvokeError(response["errorMessage"])

    code = response.get("statusCode", None)
    if code == 400:
        print("Error! (statusCode: 400)\n")
        err = json.loads(response["body"])
        if "traceback" in err:
            raise InvokeError(err, err["traceback"])
        else:
            # FIXME
            raise InvokeError(err, err)

    if code != 200:
        raise ValueError(f"Unexpected response code: {code}")

    body = json.loads(response["body"]) if as_json else response["body"]
    if verbose:
        pprint.pprint(body)

    return body


@timed
def _invoke(args):
    from ..config import load

    cfg = load(config_file=Path(args["--config"]))
    payload = {
        "function": args["--fn"],
        "args": args["ARG"],
        "timeout": cfg.service.lambda_timeout,
    }
    data = _call_cloud_api(
        "new", payload, Path(args["--config"]), verbose=args["--verbose"]
    )
    print(data["result"])


@timed
def _events(args):
    from ..executors import awslambda

    data = _call_cloud_api(
        "get_events",
        {"session_id": args["SESSION_ID"]},
        Path(args["--config"]),
        verbose=args["--verbose"],
    )
    if args["--unified"]:
        awslambda.print_events_unified(data)
    elif args["--json"]:
        print(json.dumps(data, indent=2))
    else:
        awslambda.print_events_by_machine(data)


@timed
def _logs(args):
    from ..executors import awslambda

    data = _call_cloud_api(
        "get_output",
        {"session_id": args["SESSION_ID"]},
        Path(args["--config"]),
        verbose=args["--verbose"],
    )
    awslambda.print_outputs(data)


def main():
    colorama.init()
    args = docopt(__doc__, version=__version__)
    if args["--vverbose"]:
        logging.basicConfig(level=logging.DEBUG)
        LOG.debug(args)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)

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
        print(em("Invalid command line.\n"))
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
