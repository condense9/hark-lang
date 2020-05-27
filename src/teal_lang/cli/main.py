"""Teal.

Usage:
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy FILE URL
  teal [options] FILE [ARG...]

Commands:
  asm      Compile a file and print the bytecode listing.
  ast      Create a data flow graph (PNG)
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

import colorama
from colorama import Back, Fore, Style

from docopt import docopt

from .. import __version__, load
from ..machine import executable

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
    exe = load.compile_file(Path(args["FILE"]))
    print(em("\nBYTECODE:"))
    print(exe.listing())
    print(em("\nBINDINGS:\n"))
    print(exe.bindings_table())
    print()


def _deploy(args):
    raise NotImplementedError


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
    if args["asm"]:
        _asm(args)
    elif args["deploy"]:
        _deploy(args)
    elif args["FILE"]:
        _run(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
