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

import os.path
import sys
import logging

from docopt import docopt
from .. import run
from .. import tealparser

from .. import __version__


def _run(args):
    fn = args["--fn"]
    filename = args["<file>"]
    fn_args = args["<fn_args>"]
    sys.path.append(".")

    if args["--storage"] == "memory":
        if args["--concurrency"] == "processes":
            raise ValueError("Can't use processes with in-memory storage")
        run.run_local(filename, fn, fn_args)

    elif args["--storage"] == "dynamodb":
        if args["--concurrency"] == "processes":
            run.run_ddb_processes(filename, fn, fn_args)
        else:
            run.run_ddb_local(filename, fn, fn_args)

    else:
        raise ValueError(args["--storage"])


def _ast(args):
    fn = args["--fn"]
    filename = args["<file>"]
    if args["--output"]:
        dest_png = args["--output"]
    else:
        dest_png = f"{os.path.splitext(filename)[0]}_{fn}.png"
    tealparser.make_ast(filename, fn, dest_png)


def _asm(args):
    toplevel = tealparser.load_file(args["<file>"])
    exe = tealparser.make_exe(toplevel)
    print(exe.listing())


# def _deploy(args):
#     requests


def main():
    args = docopt(__doc__, version=__version__)
    if args["--vverbose"]:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug(args)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)

    if args["ast"]:
        _ast(args)
    elif args["asm"]:
        _asm(args)
    elif args["<file>"]:
        _run(args)
    elif args["<deploy>"]:
        _deploy(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
