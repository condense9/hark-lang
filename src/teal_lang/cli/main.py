"""Teal.

Usage:
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy [--config CONFIG]
  teal [options] destroy [--config CONFIG]
  teal [options] invoke [--config CONFIG]
  teal [options] FILE [ARG...]
  teal --version
  teal --help

Commands:
  asm      Compile a file and print the bytecode listing.
  ast      Create a data flow graph (PNG).
  deploy   Deploy to the cloud.
  destroy  Remove cloud deployment.
  invoke   Invoke a teal function in the cloud.
  default  Run a Teal function locally.

General options:
  -h, --help      Show this screen.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --version       Show version.

  -f FUNCTION, --fn=FUNCTION   Function to run      [default: main]
  -s MODE, --storage=MODE      memory | dynamodb    [default: memory]
  -c MODE, --concurrency=MODE  processes | threads  [default: threads]

  -o OUTPUT  Name of the output file

  --config CONFIG  Config file to use  [default: teal.toml]

Arguments:
  FILE  Main Teal file
  ARG   Function arguments [default: None]
  URL   Base URL to deploy to
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

import pprint
import json
import colorama
from colorama import Back, Fore, Style

from .. import __version__

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


def em(string):
    return Style.BRIGHT + string + Style.RESET_ALL


def _asm(args):
    from .. import load

    exe = load.compile_file(Path(args["FILE"]))
    print(em("\nBYTECODE:"))
    print(exe.listing())
    print(em("\nBINDINGS:\n"))
    print(exe.bindings_table())
    print()


def _deploy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load(config_file=Path(args["--config"]), create_deployment_id=True)

    # Deploy the infrastructure (idempotent)
    aws.deploy(cfg)
    api = aws.get_api()

    logs, response = api.version.invoke(cfg, {})
    print("Teal:", json.loads(response)["body"])

    # Deploy the teal code
    with open(cfg.service.teal_file) as f:
        content = f.read()

    exe_payload = {"content": content}
    logs, response = api.set_exe.invoke(cfg, exe_payload)

    print("Done.")


def _destroy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load(config_file=Path(args["--config"]))
    aws.destroy(cfg)
    print("Done.")


def _invoke(args):
    from ..cloud import aws
    from ..config import load

    api = aws.get_api()
    cfg = load(config_file=Path(args["--config"]))

    # See teal_lang/executors/awslambda.py
    logs, response = api.new.invoke(cfg, dict(function=args["--fn"], args=args["ARG"]))
    if args["--verbose"]:
        print(logs)

    response = json.loads(response)

    if response.get("statusCode", None) == 400:
        print("Teal error! (statusCode == 400)\n")
        err = json.loads(response["body"])
        print("\n".join(err["traceback"]))

    if response.get("statusCode", None) == 200:
        data = json.loads(response["body"])
        if args["--verbose"]:
            pprint.pprint(data)
        print(data["result"])


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
    elif args["FILE"]:
        _run(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
