"""Top-level utilities for loading Teal code"""
import sys
from pathlib import Path

from .machine.executable import Executable
from .cli.styling import em
from .teal_compiler import tl_compile
from .teal_parser.parser import tl_parse, TealSyntaxError


def compile_text(text: str) -> Executable:
    "Parse and compile a Teal program"
    return tl_compile(tl_parse(text))


# Compute column.
#     input is the input text string
#     token is a token instance
def find_column(text, token):
    last_cr = text.rfind("\n", 0, token.index)
    if last_cr < 0:
        last_cr = 0
    column = (token.index - last_cr) + 1
    return column


def msg(text, exc, filename):
    msg = f"{filename}:{exc.token.lineno} ~ {exc.msg}"
    line = text.split("\n")[exc.token.lineno - 1]
    msg += em(f"\n\n {line}\n")
    msg += " " * (find_column(text, exc.token) - 1) + "^"
    return msg


def compile_file(filename: Path) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    try:
        return compile_text(text)
    except TealSyntaxError as exc:
        print(msg(text, exc, filename))
        sys.exit(1)


if __name__ == "__main__":
    import sys
    import pprint

    with open(sys.argv[1], "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    exe = tl_compile(tl_parse(text, debug_lex=debug))

    print(exe.listing())
