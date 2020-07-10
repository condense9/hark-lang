"""Top-level utilities for loading Teal code"""
import sys
from pathlib import Path

from .teal_compiler.compiler import TealCompileError
from .cli.interface import bad, neutral
from .machine.executable import Executable
from .teal_compiler import tl_compile
from .teal_parser.parser import TealParseError, tl_parse


def compile_text(text: str) -> Executable:
    "Parse and compile a Teal program"
    return tl_compile(tl_parse("<unknown>", text))


def compile_file(filename: Path) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    return tl_compile(tl_parse(filename, text))


if __name__ == "__main__":
    import sys
    import pprint

    filename = sys.argv[1]
    with open(filename, "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    exe = tl_compile(tl_parse(filename, text, debug_lex=debug))

    print(exe.listing())
