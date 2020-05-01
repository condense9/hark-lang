"""Teal Compiler.

Usage:
  teal [options] ast <file> [--output=OUTPUT]
  teal [options] asm <file>
  teal [options] deploy <file> <url>
  teal [options] <file> [<fn_args>...]

Commands:
  ast   Create a PNG representation of the Abstract Syntax Tree of a function
  asm   Compile a file and print the bytecode listing

Options:
  -h, --help      Show this screen.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --version       Show version.

  -f FUNCTION, --fn=FUNCTION  Function for run/AST [default: main]
  -o OUTPUT, --output=OUTPUT  Destination file

  -s MODE, --storage=MODE      (memory|dynamodb)   [default: memory]
  -c MODE, --concurrency=MODE  (processes|threads) [default: threads]

Arguments:
  FILE     Teal file to read
  FN_ARGS  Arguments to pass to the executable [default: None].
  URL      Base URL to deploy to
"""

# Tools:
# - pyfiglet https://github.com/pwaller/pyfiglet
# - typer? https://typer.tiangolo.com/
# - colorama https://pypi.org/project/colorama/

import sys
import logging
from pathlib import Path

from docopt import docopt
from .. import tealparser
from ..tealparser.read import read_exp

from .. import __version__

LOG = logging.getLogger(__name__)


def _run(args):
    fn = args["--fn"]
    filename = args["<file>"]
    sys.path.append(".")

    # FIXME - should argv just always be strings? But then you can't pass in
    # arbitrary types to other functions. We need a single interface.
    fn_args = [read_exp(arg) for arg in args["<fn_args>"]]

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
    filename = Path(args["<file>"])

    if args["--output"]:
        dest_png = args["--output"]
    else:
        dest_png = f"{filename.stem}_{fn}.png"
    tealparser.make_ast(filename, fn, dest_png)


def _asm(args):
    toplevel = tealparser.load_file(args["<file>"])
    exe = tealparser.make_exe(toplevel)
    print(exe.listing())


def _deploy(args):
    raise NotImplementedError


def main():
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
    elif args["<file>"]:
        _run(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
