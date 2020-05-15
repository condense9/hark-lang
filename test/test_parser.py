import pytest

from teal_lang.teal_parser.parser import *


TOP_STMTS = [
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


@pytest.mark.parametrize("text", TOP_STMTS, ids=range(len(TOP_STMTS)))
def test_parse(text):
    text = text.strip() + "\n"
    parser = TealParser()
    lexer = TealLexer()

    toks = list(post_lex(lexer.tokenize(text)))
    assert toks

    print(list((tok.type, tok.value) for tok in toks))

    res = parser.parse(iter(toks))
    assert res
