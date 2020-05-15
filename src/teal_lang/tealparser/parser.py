from ast import literal_eval
from dataclasses import dataclass
from typing import Any

from sly import Lexer, Parser
from sly.lex import Token


class TealLexer(Lexer):
    tokens = {
        # whitespace
        INDENT,
        DEDENT,
        NL,
        # identifiers and keywords
        ID,
        DEF,
        IF,
        ELIF,
        ELSE,
        IMPORTPY,
        FROM,
        AS,
        ASYNC,
        AWAIT,
        # values
        NUMBER,
        STRING,
        # operators
        ADD,
        SUB,
        MUL,
        DIV,
        AND,
        OR,
        EQ,
        SET,  # must come after EQ
    }
    literals = {"(", ")", ":", ","}

    ignore_comment = r"\#.*"
    ignore_ws = r"(?<=\S)[ \t]+"

    NL = r"[\r\n]+\s*"

    # Identifiers and keywords
    ID = "[a-z][a-zA-Z0-9_?.]*"
    ID["def"] = DEF
    ID["if"] = IF
    ID["elif"] = ELIF
    ID["else"] = ELSE
    ID["importpy"] = IMPORTPY
    ID["from"] = FROM
    ID["as"] = AS
    ID["async"] = ASYNC
    ID["await"] = AWAIT

    # values
    NUMBER = r"[+-]?[\d.]+"
    STRING = r'"[^\"]+"'

    # Special symbols
    ADD = r"\+"
    SUB = r"-"
    MUL = r"\*"
    DIV = r"/"
    EQ = r"=="
    SET = r"="
    AND = r"&&"
    OR = r"\|\|"

    def error(self, t):
        print("Illegal character '%s'" % t.value[0])
        self.index += 1


def make_tok(t, v="gen", lineno=None, index=None):
    tok = Token()
    tok.type = t
    tok.value = v
    tok.lineno = lineno
    tok.index = index
    return tok


def post(toks):
    size = 0
    levels = {0: 0}
    level = 0
    indent = make_tok("INDENT")
    dedent = make_tok("DEDENT")
    t = next(toks)
    for next_tok in toks:
        yield t

        if t.type == "NL":
            new_size = len(t.value.replace("\n", "").replace("\r", ""))
            if new_size > size:
                size = new_size
                level += 1
                levels[size] = level
                yield indent
            elif new_size < size:
                size = new_size
                if size not in levels:
                    raise Exception(f"Irregular indentation! {size}, {levels}")
                while level > levels[size]:
                    level -= 1
                    yield dedent
                    if next_tok.type not in ("ELSE", "ELIF"):
                        yield t
        t = next_tok

    yield t

    # and add missing "dedents"
    nl = make_tok("NL")
    while level > 0:
        yield dedent
        level -= 1
        yield nl


def lexrepl():
    lexer = TealLexer()
    while True:
        try:
            text = input("lex > ")
        except EOFError:
            break
        if text:
            print(list((tok.type, tok.value) for tok in post(lexer.tokenize(text))))


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
        toks = post(lexer.tokenize(text))
        print(list((tok.type, tok.value) for tok in toks))


### PARSER


@dataclass
class N_Definition:
    name: str
    paramlist: list
    body: list


@dataclass
class N_Import:
    name: str
    mod: str
    as_: str


@dataclass
class N_Call:
    fn: str
    args: list


@dataclass
class N_Async:
    call: N_Call


@dataclass
class N_Await:
    expr: list


@dataclass
class N_Binop:
    lhs: Any
    op: str
    rhs: Any


@dataclass
class N_If:
    cond: Any
    then: list
    els: list


@dataclass
class N_Progn:
    exprs: list


@dataclass
class N_Id:
    name: str


@dataclass
class N_Literal:
    value: Any


class TealParser(Parser):
    debugfile = "parser.out"
    tokens = TealLexer.tokens
    precedence = (
        # ("nonassoc", LESSTHAN, GREATERTHAN),
        ("right", OR),
        ("right", AND),
        ("nonassoc", EQ, SET),
        ("left", ADD, SUB),
        ("left", MUL, DIV),
        ("right", ASYNC, AWAIT, DEF),
    )

    start = "top"

    @_("suite")
    def top(self, p):
        return p.suite

    @_("")
    def nothing(self, p):
        pass

    @_("expr nls more_suite")
    def suite(self, p):
        return [p.expr] + p.more_suite

    @_("NL more_nls")
    def nls(self, p):
        pass

    @_("nothing")
    def more_nls(self, p):
        pass

    @_("NL more_nls")
    def more_nls(self, p):
        pass

    @_("nothing")
    def more_suite(self, p):
        return []

    @_("expr NL more_suite")
    def more_suite(self, p):
        return [p.expr] + p.more_suite

    # imports

    @_("IMPORTPY ID FROM ID import_as")
    def expr(self, p):
        return N_Import(p.ID0, p.ID1, p.import_as)

    @_("nothing")
    def import_as(self, p):
        return None

    @_("AS ID")
    def import_as(self, p):
        return p.ID

    # definitions (functions only, for now)

    @_("DEF ID '(' paramlist ')' ':' expr")
    def expr(self, p):
        return N_Definition(p.ID, p.paramlist, p.expr)

    @_("nothing")
    def paramlist(self, p):
        return []

    @_("ID")
    def paramlist(self, p):
        return [p.ID]

    @_("ID ',' paramlist")
    def paramlist(self, p):
        return [p.ID] + p.paramlist

    # block (progn)

    @_("NL INDENT suite DEDENT")
    def expr(self, p):
        return N_Progn(p.suite)

    # sub

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    # async/await

    @_("ASYNC expr")
    def expr(self, p):
        return N_Async(p.expr)

    @_("AWAIT expr")
    def expr(self, p):
        return N_Await(p.expr)

    # function call

    @_("expr '(' arglist ')'")
    def expr(self, p):
        return N_Call(p.expr, p.arglist)

    @_("nothing")
    def arglist(self, p):
        return []

    @_("expr")
    def arglist(self, p):
        return [p.expr]

    @_("expr ',' arglist")
    def arglist(self, p):
        return [p.expr] + p.arglist

    # conditional

    @_("IF expr ':' expr rest_if")
    def expr(self, p):
        return N_If(p.expr0, p.expr1, p.rest_if)

    @_("nothing")
    def rest_if(self, p):
        return []

    @_("ELIF expr ':' expr rest_if")
    def rest_if(self, p):
        return [N_If(p.expr0, p.expr1, p.rest_if)]

    @_("ELSE ':' expr")
    def rest_if(self, p):
        return p.expr

    # binops

    @_(
        "expr ADD expr",
        "expr SUB expr",
        "expr MUL expr",
        "expr DIV expr",
        "expr AND expr",
        "expr OR expr",
        "expr EQ expr",
        "expr SET expr",
    )
    def expr(self, p):
        return N_Binop(p[0], p[1], p[2])

    # literals

    @_("ID")
    def expr(self, p):
        return N_Id(p.ID)

    @_("NUMBER")
    def expr(self, p):
        return N_Literal(literal_eval(p.NUMBER))

    @_("STRING")
    def expr(self, p):
        return N_Literal(literal_eval(p.STRING))


def do_parse(text, debug=True):
    parser = TealParser()
    lexer = TealLexer()
    print("\n---")
    print(text.strip())
    print(":")
    toks = list(post(lexer.tokenize(text)))
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
        print(do_parse(text))


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


###


def parse(text, debug_lex=False):
    parser = TealParser()
    lexer = TealLexer()
    text = text.strip() + "\n"
    if debug_lex:
        toks = list(post(lexer.tokenize(text)))
        indent = 0
        for tok in toks:
            val = ""
            if tok.type not in ("NL", "INDENT", "DEDENT") and tok.type != tok.value:
                val = tok.value
            space = " " * indent
            print(f"{space}{tok.type:10} : {val}")
            if tok.type == "INDENT":
                indent += 2
            elif tok.type == "DEDENT":
                indent -= 2
        return parser.parse(iter(toks))
    else:
        return parser.parse(post(lexer.tokenize(text)))


if __name__ == "__main__":
    # testlex()
    # lexrepl()
    testparse()
    # parserepl()
