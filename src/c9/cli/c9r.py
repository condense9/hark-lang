"""C9 Run.

Usage:
  c9r [-h] [--moddir <dir>] <executable> [<arg>]...

Run the executable with some arguments.

Options:
  --moddir DIR  Directory with Python modules this executable uses
  -h, --help    Show help

"""

from docopt import docopt

import sys
import os.path
from ..constants import C9_VERSION
from ..machine import c9e

from ..runtimes import local


def run(exe_path, args, moddir=None):
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


def main(args):
    run(args["<executable>"], args["<arg>"], args["--moddir"])


if __name__ == "__main__":
    arguments = docopt(__doc__, version=C9_VERSION)
    main(arguments)
