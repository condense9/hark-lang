"""Top-level utilities for loading Teal code"""
import sys
from pathlib import Path

from .teal_compiler.compiler import CompileError
from .cli.interface import bad, neutral
from .machine.executable import Executable
from .teal_compiler import tl_compile
from .teal_parser.parser import TealSyntaxError, tl_parse, token_column


def compile_text(text: str) -> Executable:
    "Parse and compile a Teal program"
    return tl_compile(tl_parse(text))


def error_msg(text, exc, filename) -> str:
    """Get an error message explaining why compilation failed"""
    # TODO add debug info to the CompileError class and unify this
    if isinstance(exc, CompileError):
        return bad("Compilation failed.\n") + str(exc)
    else:
        msg = bad(f"{filename}:{exc.token.lineno} ~ {exc.msg}")
        line = text.split("\n")[exc.token.lineno - 1]
        msg += neutral(f"\n\n {line}\n")
        msg += " " * (token_column(text, exc.token.index) - 1) + "^"
        return msg


def compile_file(filename: Path) -> Executable:
    "Compile a Teal file, creating an Executable ready to be used"
    with open(filename, "r") as f:
        text = f.read()

    try:
        return compile_text(text)
    except (TealSyntaxError, CompileError) as exc:
        print(error_msg(text, exc, filename))
        sys.exit(1)


if __name__ == "__main__":
    import sys
    import pprint

    with open(sys.argv[1], "r") as f:
        text = f.read()

    debug = len(sys.argv) > 2 and sys.argv[2] == "-d"
    exe = tl_compile(tl_parse(text, debug_lex=debug))

    print(exe.listing())
