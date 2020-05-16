"""Top-level utilities for loading Teal code"""

from pathlib import Path

from .machine.executable import Executable, link
from .teal_compiler import tl_compile
from .teal_parser import tl_parse


def compile_text(text: str, *, debug_lex=False) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    bindings, functions = tl_compile(tl_parse(text, debug_lex=debug_lex))
    return link(bindings, functions)


def compile_file(filename: Path, *, debug_lex=False) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    return compile_text(text, debug_lex=debug_lex)


if __name__ == "__main__":
    import sys
    import pprint

    with open(sys.argv[1], "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    bindings, functions = tl_compile(tl_parse(text, debug_lex=debug))

    pprint.pprint(bindings)
    print("")
    pprint.pprint(functions)

    print(link(bindings, functions).listing())
