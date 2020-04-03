"""C9 Compiler.

Usage:
  c9c [options] handler <file> <attribute> [--output=<file>]
  c9c [options] service <file> <attribute> [--output=<file>] [--include=<path>]...

Commands:
  handler  Generate a C9E executable file.
  service  Generate a deployable service object.

Arguments:
  FILE        Python file containing the Service object.
  ATTRIBUTE   Name of the Service object in FILE.

Options:
  -h, --help     Show this screen.
  -v, --verbose  Be verbose.
  --version      Show version.

  (shared)
  -o FILE, --output=FILE   Output file (derived from ATTRIBUTE otherwise).

  (service only)
  -I PATH, --include=PATH  Include PATH in the service object.
  --include-all            Include all files in the same directory as FILE
  --split-handlers         Generate one service object for each executable.


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

from docopt import docopt
from schema import Schema, And, Or, Use, SchemaError

from .. import packer
from ..constants import C9_VERSION


def dir_exists(x):
    return x == "" or os.path.exists(x)


def file_does_not_exist(x):
    return not os.path.exists(x)


def main(args):
    ext = ".c9e" if args["handler"] else ".zip"

    if not args["--output"]:
        args["--output"] = args["<attribute>"].lower() + ext

    args["output_dir"] = os.path.dirname(args["--output"])

    schema = Schema(
        {
            "<file>": Use(open, error=f"{args['<file>']} is not readable"),
            "output_dir": And(
                dir_exists, error=f"Directory \"{args['output_dir']}\" doesn't exist"
            ),
            "--output": file_does_not_exist,
        },
        ignore_extra_keys=True,
    )

    try:
        # print(args)
        schema.validate(args)
    except SchemaError as e:
        exit(e)

    main_file = args["<file>"]
    attribute = args["<attribute>"]
    output = args["--output"]

    if args["handler"]:
        packer.pack_handler(main_file, attribute, output)
    elif args["service"]:
        include = args["--include"]
        if args["--split-handlers"]:
            raise NotImplementedError("Split handlers not implemented yet!")
        packer.pack_service_lambda(
            main_file, attribute, output, include, args["--include-all"]
        )
    else:
        raise NotImplementedError


if __name__ == "__main__":
    arguments = docopt(__doc__, version=C9_VERSION)
    main(arguments)
