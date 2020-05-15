import os
from ast import literal_eval
from typing import Any

from sly import Lexer, Parser
from sly.lex import Token

from . import nodes


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
        TRUE,
        FALSE,
        # operators
        ADD,
        SUB,
        MUL,
        DIV,
        AND,
        OR,
        EQ,
        GT,
        LT,
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
    ID["true"] = TRUE
    ID["false"] = FALSE

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
    GT = r">"
    LT = r"<"
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


def post_lex(toks):
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


### PARSER


class TealParser(Parser):
    tokens = TealLexer.tokens
    precedence = (
        ("nonassoc", LT, GT),
        ("right", OR),
        ("right", AND),
        ("nonassoc", EQ, SET),
        ("left", ADD, SUB),
        ("left", MUL, DIV),
        # ("right", ASYNC, AWAIT, DEF),
    )

    start = "top"

    @_("suite")
    def top(self, p):
        return p.suite

    @_("")
    def nothing(self, p):
        pass

    # suites

    @_("suite_item more_suite")
    def suite(self, p):
        return p.suite_item + p.more_suite

    @_("nothing")
    def more_suite(self, p):
        return []

    @_("suite_item more_suite")
    def more_suite(self, p):
        return p.suite_item + p.more_suite

    @_("expr NL")
    def suite_item(self, p):
        return [p.expr]

    @_("NL")
    def suite_item(self, p):
        return []

    # imports

    @_("IMPORTPY ID FROM ID import_as")
    def expr(self, p):
        return nodes.N_Import(p.ID0, p.ID1, p.import_as)

    @_("nothing")
    def import_as(self, p):
        return None

    @_("AS ID")
    def import_as(self, p):
        return p.ID

    # definitions (functions only, for now)

    @_("DEF ID '(' paramlist ')' ':' expr")
    def expr(self, p):
        return nodes.N_Definition(p.ID, p.paramlist, p.expr)

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
        return nodes.N_Progn(p.suite)

    # sub

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    # function call

    @_("expr '(' arglist ')'")
    def expr(self, p):
        return nodes.N_Call(p.expr, p.arglist)

    @_("nothing")
    def arglist(self, p):
        return []

    @_("expr")
    def arglist(self, p):
        return [p.expr]

    @_("expr ',' arglist")
    def arglist(self, p):
        return [p.expr] + p.arglist

    # async/await

    @_("ASYNC expr")
    def expr(self, p):
        return nodes.N_Async(p.expr)

    @_("AWAIT expr")
    def expr(self, p):
        return nodes.N_Await(p.expr)

    # conditional

    @_("IF expr ':' expr rest_if")
    def expr(self, p):
        return nodes.N_If(p.expr0, p.expr1, p.rest_if)

    @_("nothing")
    def rest_if(self, p):
        return []

    @_("ELIF expr ':' expr rest_if")
    def rest_if(self, p):
        return [nodes.N_If(p.expr0, p.expr1, p.rest_if)]

    @_("ELSE ':' expr")
    def rest_if(self, p):
        return p.expr

    # binops

    @_(
        "expr GT expr",
        "expr LT expr",
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
        return nodes.N_Binop(p[0], p[1], p[2])

    # literals

    @_("ID")
    def expr(self, p):
        return nodes.N_Id(p.ID)

    @_("TRUE")
    def expr(self, p):
        return nodes.N_Literal(True)

    @_("FALSE")
    def expr(self, p):
        return nodes.N_Literal(False)

    @_("NUMBER")
    def expr(self, p):
        return nodes.N_Literal(literal_eval(p.NUMBER))

    @_("STRING")
    def expr(self, p):
        return nodes.N_Literal(literal_eval(p.STRING))


###


def tl_parse(text, debug_lex=False):
    parser = TealParser()
    lexer = TealLexer()
    text = text.strip() + "\n"
    if debug_lex:
        toks = list(post_lex(lexer.tokenize(text)))
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
        return parser.parse(post_lex(lexer.tokenize(text)))
