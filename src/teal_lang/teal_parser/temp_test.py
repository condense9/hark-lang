"""TODO - move to tests"""

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


stream = [
    "bla",
    "123",
    '"bla"',
    "123.45",
    "-5",
    "a.b",
    "bla34_dsa",
    "bar # foo\nbaz",
    "def foo:\n  bar",
    "foo   bar\n  baz",
    "foo\n  bar\n    baz",
    "foo\n  bar\n  cow\n    baz",
]


def testlex():
    for text in stream:
        lexer = TealLexer()
        print("---")
        print(text)
        print(":")
        toks = post_lex(lexer.tokenize(text))
        print(list((tok.type, tok.value) for tok in toks))


def do_parse(text, debug=True):
    parser = TealParser()
    lexer = TealLexer()
    print("\n---")
    print(text.strip())
    print(":")
    toks = list(post_lex(lexer.tokenize(text)))
    if debug:
        print(list((tok.type, tok.value) for tok in toks))
    return parser.parse(iter(toks))


exprs = [
    "foo",
    "foo()",
    "foo(1)",
    "foo(1, 2, 3)",
    "foo(1, g(), 3)",
    "1 + 2",
    "1 + 2 + 3",
    "1 + 2 * 3",
    "(1 + 2) * 3",
    "1 + (foo() + 4)",
]


top_stmts = [
    "importpy foo from bar.baz",
    "importpy foo from bar.baz as cow",
    "def foo(): 1",
    "def foo(): g()()",
    "def foo(x):\n    x",
    """def foo():
    1
    2
""",
    """
def bla(x):
    if x: 1
""",
    """
def bla(x):
    if x:
        1
""",
    """importpy foo from bar.baz as cow

def bla(x):
    1
    """,
    """
def bla(x):
    if x:
        1
    else:
        2
    """,
    """
def bla(x):
    if x: 1 else: 2
    """,
    """
def bla(x):
    if x:
        1
    elif y:
        3
    else:
        4
        5
""",
    "def f(): async g()",
    "def f(): g()\ndef g(): 1",
    """def foo():
    1

def bar():
    2""",
    """# comment start

def foo():
    # comment inline
    1
    # another
    2
""",
]


def testparse():
    if TealParser.start == "top":
        values = [t.strip() + "\n" for t in top_stmts]
    elif TealParser.start == "expr":
        values = exprs
    else:
        raise ValueError(TealParser.start)

    max_test = None
    for text in values[:max_test]:
        res = do_parse(text)
        print(res)
        if not res:
            raise Exception("Failed")


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
