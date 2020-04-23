"""runit.

Usage:
  runit <c9_file> [args...]

Arguments:
  C9_FILE  The file to run
  ARGS     argv [default = []]

"""
from parser import make_parser
import transformer
from docopt import docopt


def main():
    args = docopt(__doc__, version="0.1")
    parser = make_parser()

    with open(args["<c9_file>"]) as f:
        content = f.read()

    tree = parser.parse(content.strip() + "\n")
    print(tree.pretty())

    functions = transformer.get_functions(tree)

    # exe = link(functions)
    # local.run(exe, args["args"])


if __name__ == "__main__":
    main()
