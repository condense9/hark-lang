"""C9 Compiler.

Usage:
  c9 [options] build <module> <attribute>
  c9 [options] compile <module> <attribute> <package>
  c9 [options] run <file> [<arg>...]
  c9 [options] graph [--legend] <module> <attribute>

Commands:
  build    Generate a C9E executable file for the handler.
  compile  Generate a deployable service object.
  run      Run a C9E executable.
  graph    Build a graph of a function execution

Arguments:
  MODULE      Python module (eg a.b.c) containing the Service object.
  ATTRIBUTE   Name of the Service object in FILE.

Options:
  -h, --help     Show this screen.
  -v, --verbose  Be verbose.
  --version      Show version.

  (build, compile)
  -o FILE, --output=FILE   Output file (derived from ATTRIBUTE otherwise).

  (compile only)
  PACKAGE           Top level Python package to include
  --dev             Use the development synthesis pipeline.
  --libs=LIBS       Directory with python libaries to include
  --split-handlers  Generate one service object for each executable.

  (run only)
  FILE          C9E executable file to run
  --moddir=DIR  Directory with Python modules this executable uses.
  ARG...        Arguments to pass to the executable [default = None].

  (graph only)
  --legend  Include the legend [default = False]

===

Examples:

c9c handler file.py main

Generate file "main.c9e", containing the executable of file.main

===

c9c service file.py SERVICE

Generate "service.zip", containing the lambda for all handlers in SERVICE.

===

c9c service file.py SERVICE --split-handlers

Generate a lambda zip for each handler in SERVICE

===

c9c service file.py SERVICE --include fileb.py -Idir -o foo.zip

Generate a foo.zip for SERVICE, also packaging "fileb.py" and "dir".
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
from ..synthesiser import visualise

from ..runtimes import local


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
    print(local.run(exe, [args]).result)
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
    graph = visualise.make_complete_graph(fn, include_legend=args["--legend"])
    print(graph.source)


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
