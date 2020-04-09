"""C9 Compiler.

Usage:
  c9 [options] (build | compile) <file> <attribute>
  c9 [options] run <file> [<arg>...]

Commands:
  build    Generate a C9E executable file for the handler.
  compile  Generate a deployable service object.
  run      Run a C9E executable.

Arguments:
  FILE        Python file containing the Service object.
  ATTRIBUTE   Name of the Service object in FILE.

Options:
  -h, --help     Show this screen.
  -v, --verbose  Be verbose.
  --version      Show version.

  (build, compile)
  -o FILE, --output=FILE   Output file (derived from ATTRIBUTE otherwise).

  (compile only)
  --split-handlers  Generate one service object for each executable.
  --dev             Use the development synthesis pipeline.

  (run only)
  --moddir=DIR  Directory with Python modules this executable uses.
  ARG...        Arguments to pass to the executable [default = None].


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

from docopt import docopt
from schema import And, Or, Schema, SchemaError, Use

from .. import __version__
from .. import packer
from ..machine import c9e

from ..runtimes import local


def dir_exists(x):
    return x == "" or os.path.exists(x)


def file_does_not_exist(x):
    return not os.path.exists(x)


def _run(args):
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
    if not args["--output"]:
        args["--output"] = args["<attribute>"].lower() + ".c9e"

    schema = Schema(
        {
            "<file>": Use(open, error=f"{args['<file>']} is not readable"),
            "--output": Use(file_does_not_exist),
        },
        ignore_extra_keys=True,
    )
    try:
        schema.validate(args)
    except SchemaError as e:
        exit(e)

    packer.pack_handler(
        args["<file>"], args["<attribute>"], args["--output"], verbose=args["--verbose"]
    )


def _compile(args):
    if not args["--output"]:
        args["--output"] = args["<attribute>"].lower()

    schema = Schema(
        {
            "--output": Use(
                dir_exists, error=f"Directory \"{args['--output']}\" doesn't exist",
            ),
        },
        ignore_extra_keys=True,
    )
    try:
        schema.validate(args)
    except SchemaError as e:
        exit(e)

    if args["--split-handlers"]:
        raise NotImplementedError("Split handlers not implemented yet!")

    packer.pack_deployment(
        args["<file>"],
        args["<attribute>"],
        args["--output"],
        dev_pipeline=args["--dev"],
        verbose=args["--verbose"],
    )


def main():
    args = docopt(__doc__, version=__version__)
    # print(args)

    if args["run"]:
        _run(args)
    elif args["compile"]:
        _compile(args)
    elif args["build"]:
        _build(args)
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
