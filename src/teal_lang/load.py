"""Top-level utilities for loading Teal code"""

from pathlib import Path

from .machine.executable import Executable
from .teal_compiler import tl_compile
from .teal_parser import tl_parse


def compile_text(text: str) -> Executable:
    "Parse and compile a Teal program"
    return tl_compile(tl_parse(text))


def compile_file(filename: Path) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    return compile_text(text)


if __name__ == "__main__":
    import sys
    import pprint

    with open(sys.argv[1], "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    exe = tl_compile(tl_parse(text, debug_lex=debug))

    print(exe.listing())
