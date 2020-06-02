"""Teal.

Usage:
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy [--stage STAGE]
  teal [options] destroy [--stage STAGE]
  teal [options] FILE [ARG...]
  teal --version
  teal --help

Commands:
  asm      Compile a file and print the bytecode listing.
  ast      Create a data flow graph (PNG).
  deploy   Deploy to the cloud.
  destroy  Remove cloud deployment.
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

  --stage STAGE  Stage to deploy  (dev | prod)  [default: dev]

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

    cfg = load(create_deployment_id=True)
    api = aws.deploy(cfg)

    logs, response = api.version.invoke(cfg, {})

    print("Version:", json.loads(response))

    with open(cfg.service.teal_file) as f:
        content = f.read()

    exe_payload = {"content": content}
    logs, response = api.set_exe.invoke(cfg, exe_payload)

    print("Done.")


def _destroy(args):
    from ..cloud import aws
    from ..config import load

    cfg = load()
    aws.destroy(cfg)
    print("Done.")


def _pkg(args):
    """Get Teal lambda ZIP"""
    if not args["--dev"]:
        raise NotImplementedError("Only --dev supported for now")

    if args["-o"]:
        dest_zip = args["-o"]
    else:
        dest_zip = "teal_lambda.zip"

    root = Path(__file__).parents[3]
    script = root / "scripts" / "make_lambda_dist.sh"

    if dest_zip.exists():
        print(f"{dest_zip} already exists.")
    else:
        print("Building Teal Lambda pacakge...")
        output = subprocess.check_output([str(script), str(dest_zip)])
        print(output.decode())


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
    elif args["FILE"]:
        _run(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
