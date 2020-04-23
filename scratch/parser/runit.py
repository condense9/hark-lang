"""runit.

Usage:
  runit <c9_file>

Arguments:
  C9_FILE  The file to run

"""
from parser import make_parser
from docopt import docopt

# Node : Branch | Terminal
#
# Branch : Funcall Node*
#        | ForeignCall Node*
#        | If cond then else
#        | Do Node*
#        | Asm (?)
#
# Terminal: Literal | Symbol


def main():
    args = docopt(__doc__, version="0.1")
    parser = make_parser()

    with open(args["<c9_file>"]) as f:
        content = f.read()

    tree = parser.parse(content.strip() + "\n")
    print(tree.pretty())


if __name__ == "__main__":
    main()
