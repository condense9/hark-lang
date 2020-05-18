"""REPLs for testing parsing/lexing"""

from .parser import *


def lexrepl():
    lexer = TealLexer()
    while True:
        try:
            text = input("lex > ")
        except EOFError:
            break
        if text:
            print(list((tok.type, tok.value) for tok in post_lex(lexer.tokenize(text))))


def parserepl():
    if TealParser.start != "expr":
        print("! Set TealParser.start to 'expr' to use the REPL")
        return

    while True:
        try:
            text = input("expr > ")
        except EOFError:
            break
        if text:
            do_parse(text, debug=False)


if __name__ == "__main__":
    # testlex()
    # lexrepl()
    testparse()
    # parserepl()
