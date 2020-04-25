"""C9 Compiler.

Usage:
  c9 [options] init [dir]
  c9 [options] run [--fn=FUNCTION] <file> [arg...]
  c9 [options] graph [--fn=FUNCTION] <file>
  c9 [options] deploy <file> <endpoint>

Commands:
  init   Initialise C9 in dir
  run    Read a C9 file and run a function in it
  graph  Read a C9 file and create an (AST) graph of a function

Init Arguments:
  DIR  Directory to initialise [default = .]

Run Arguments:
  FILE      C9 file to read
  [ARG...]  Arguments to pass to the executable [default = None].
  -f FUNCTION, --fn=FUNCTION  Function to run/graph [default = main]

Graph Arguments:
  -f FUNCTION, --fn=FUNCTION  Function to run/graph [default = main]

Options:
  -h, --help     Show this screen.
  -v, --verbose  Be verbose.
  --version      Show version.
"""

# Tools:
# - pyfiglet https://github.com/pwaller/pyfiglet
# - typer? https://typer.tiangolo.com/
# - colorama https://pypi.org/project/colorama/

import os.path
import sys
import logging

from docopt import docopt
from schema import And, Or, Schema, SchemaError, Use

from .. import __version__
from .. import packer
from ..machine import c9e
from .. import visualise

from ..runtimes import Threaded


def _run(args):
    # FIXME
    exe_path = args["<file>"]
    moddir = args["--moddir"]
    args = args["<arg>"]

    if not moddir:
        moddir = os.path.dirname(exe_path)
    try:
        exe = c9e.load(exe_path, [moddir])
    except c9e.LoadError as e:
        print("ERROR:", e)
        print("\nHint: Try passing in --moddir")
        sys.exit(1)
    # Pass the arguments as a list, like argv
    print(Threaded.run(exe, [args]).result)
    sys.exit(0)


def _build(args):
    # FIXME
    if not args["--output"]:
        args["--output"] = args["<attribute>"].lower() + ".c9e"

    packer.pack_handler(
        args["<module>"],
        args["<attribute>"],
        args["--output"],
        verbose=args["--verbose"],
    )


def _graph(args):
    fn = packer.import_handler(args["<module>"], args["<attribute>"])
    if args["--legend"]:
        raise NotImplementedError("Legend not implemented, sorry")
    visualise.print_dotviz(fn)


def _compile(args):
    if args["--split-handlers"]:
        raise NotImplementedError("Split handlers not implemented yet!")

    packer.pack_deployment(
        args["<module>"],
        args["<attribute>"],
        args["<package>"],
        build_d=args["--output"],
        libs=args["--libs"],
        dev_pipeline=args["--dev"],
        verbose=args["--verbose"],
    )


def main():
    args = docopt(__doc__, version=__version__)
    if args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
        logging.info(args)

    if args["run"]:
        _run(args)
    elif args["compile"]:
        _compile(args)
    elif args["build"]:
        _build(args)
    elif args["graph"]:
        _graph(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
