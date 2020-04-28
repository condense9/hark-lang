"""C9 Compiler.

Usage:
  c9 [options] init [<dir>]
  c9 [options] ast [<file>]
  c9 [options] asm [<file>]
  c9 [options] [<file>] [<fn_args>...]

Commands:
  init  Initialise C9 in dir
  run   Read a C9 file and run a function in it (with . in PYTHONPATH)
  ast   Read a C9 file and create an (AST) ast of a function
  asm   Compile a file and print the bytecode listing

Options:
  -h, --help      Show this screen.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --version       Show version.

  -f FUNCTION, --fn=FUNCTION  Function to run/ast [default: main]
  -o OUTPUT, --output=OUTPUT  Destination file for ast

  --storage=MODE    Storage mode (memory|dynamodb) [default: memory]
  --emulate-lamdba  Use multiple processes to emulate AWS Lambda execution

Init Arguments:
  <DIR>  Directory to initialise [default: .]

Run Arguments:
  FILE      C9 file to read
  <ARGS>  Arguments to pass to the executable [default: None].
"""

# Tools:
# - pyfiglet https://github.com/pwaller/pyfiglet
# - typer? https://typer.tiangolo.com/
# - colorama https://pypi.org/project/colorama/

import os.path
import sys
import logging

from docopt import docopt
import c9.run
import c9.parser as parser

from .. import __version__


def _run(args):
    fn = args["--fn"]
    filename = args["<file>"]
    fn_args = args["<fn_args>"]
    sys.path.append(".")

    if args["--storage"] == "memory":
        if args["--emulate-lamdba"]:
            raise ValueError("Can't emulate lambda with in-memory storage")
        c9.run.run_local(filename, fn, fn_args)

    elif args["--storage"] == "dynamodb":
        if args["--emulate-lamdba"]:
            c9.run.run_ddb_lambda_sim(filename, fn, fn_args)
        else:
            c9.run.run_ddb_local(filename, fn, fn_args)

    else:
        raise ValueError(args["--storage"])


def _ast(args):
    fn = args["--fn"]
    filename = args["<file>"]
    if args["--output"]:
        dest_png = args["--output"]
    else:
        dest_png = f"{os.path.splitext(filename)[0]}_{fn}.png"
    parser.make_ast(filename, fn, dest_png)


def _asm(args):
    toplevel = parser.load_file(args["<file>"])
    exe = parser.make_exe(toplevel)
    print(exe.listing())


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
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
