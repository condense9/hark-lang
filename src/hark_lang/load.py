"""Top-level utilities for loading Hark code"""
import os
import sys
from pathlib import Path

from .hark_compiler.compiler import HarkCompileError
from .cli.interface import bad, neutral
from .machine.executable import Executable
from .hark_compiler import tl_compile
from .hark_parser.parser import HarkParseError, tl_parse


def compile_text(text: str) -> Executable:
    "Parse and compile a Hark program"
    return tl_compile(
        tl_parse("<unknown>", text, debug_lex=os.getenv("DEBUG_LEX", False))
    )


def compile_file(filename: Path) -> Executable:
    "Compile a Hark file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    return tl_compile(tl_parse(filename, text, debug_lex=os.getenv("DEBUG_LEX", False)))


if __name__ == "__main__":
    import sys
    import pprint

    filename = sys.argv[1]
    with open(filename, "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    exe = tl_compile(tl_parse(filename, text, debug_lex=debug))

    print(exe.listing())
