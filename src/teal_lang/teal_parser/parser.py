import os
from ast import literal_eval
from typing import Any
from itertools import chain

from sly import Lexer, Parser
from sly.lex import Token

from . import nodes


class TealLexer(Lexer):
    tokens = {
        TERM,
        NL,
        SYMBOL,
        ID,
        # keywords
        FN,
        IF,
        ELIF,
        ELSE,
        ASYNC,
        AWAIT,
        TRUE,
        FALSE,
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
        GT,
        LT,
        SET,  # must come after EQ
    }
    literals = {"(", ")", ",", "{", "}"}

    ignore = r" \t"
    ignore_comment = r"//.*"
    ignore_block = r"/\*.*\*/"

    # Identifiers and keywords
    ID = "[a-z][a-zA-Z0-9_?.]*"
    ID["fn"] = FN
    ID["if"] = IF
    ID["elif"] = ELIF
    ID["else"] = ELSE
    ID["async"] = ASYNC
    ID["await"] = AWAIT
    ID["true"] = TRUE
    ID["false"] = FALSE

    SYMBOL = r":[a-z][a-zA-Z0-9_]*"

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

    TERM = r";+"

    @_(r"\n+")
    def NL(self, t):
        self.lineno = t.lineno + t.value.count("\n")
        return t

    # def error(self, t):
    #     print("Illegal character '%s'" % t.value[0])
    #     self.index += 1

    def error(self, t):
        print(
            f"{self.cls_module}.{self.cls_name}:{self.lineno}: * Illegal character",
            repr(self.text[self.index]),
        )
        self.index += 1


def post_lex(toks):
    # Add the optional terminators after lines/blocks
    term = Token()
    term.value = ";"
    term.type = "TERM"
    nl = Token()
    nl.type = "NL"

    t = next(toks)
    for next_tok in chain(toks, [nl]):
        if t.type != "NL":
            yield t
        term.lineno = t.lineno
        term.index = t.index
        if t.type == "}" and next_tok.type != "TERM":
            yield term
        elif next_tok.type == "NL" and t.type != "TERM":
            # terminate
            yield term
        t = next_tok


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
        ("right", AWAIT, ASYNC),
        ("right", "("),
    )

    start = "top"

    @_("")
    def nothing(self, p):
        pass

    # blocks

    @_("'{' expressions '}'")
    def block_expr(self, p):
        return nodes.N_Progn(p.expressions)

    @_("terminated_expr more_expressions")
    def expressions(self, p):
        return p.terminated_expr + p.more_expressions

    @_("nothing")
    def more_expressions(self, p):
        return []

    @_("terminated_expr more_expressions")
    def more_expressions(self, p):
        return p.terminated_expr + p.more_expressions

    @_("TERM")
    def terminated_expr(self, p):
        return []

    @_("expr TERM")
    def terminated_expr(self, p):
        return [p.expr]

    # TOP

    @_("nothing")
    def top(self, p):
        return []

    @_("expressions")
    def top(self, p):
        return p.expressions

    # definitions (functions only, for now)

    @_("FN '(' paramlist ')' block_expr")
    def expr(self, p):
        return nodes.N_Definition(p.paramlist, p.block_expr)

    @_("nothing")
    def paramlist(self, p):
        return []

    @_("ID")
    def paramlist(self, p):
        return [p.ID]

    @_("ID ',' paramlist")
    def paramlist(self, p):
        return [p.ID] + p.paramlist

    # function call

    @_("expr '(' arglist ')'")
    def expr(self, p):
        return nodes.N_Call(p.expr, p.arglist)

    @_("nothing")
    def arglist(self, p):
        return []

    @_("arg_item")
    def arglist(self, p):
        return [p.arg_item]

    @_("arg_item ',' arglist")
    def arglist(self, p):
        return [p.arg_item] + p.arglist

    @_("expr")
    def arg_item(self, p):
        return nodes.N_Argument(None, p.expr)

    @_("SYMBOL expr")
    def arg_item(self, p):
        # A bit icky - conflicts with SYMBOL
        return nodes.N_Argument(p.SYMBOL, p.expr)

    # sub

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    # conditional

    @_("IF expr block_expr rest_if")
    def expr(self, p):
        return nodes.N_If(p.expr, p.block_expr, p.rest_if)

    @_("nothing")
    def rest_if(self, p):
        return []

    @_("ELIF expr block_expr rest_if")
    def rest_if(self, p):
        return nodes.N_If(p.expr, p.block_expr, p.rest_if)

    @_("ELSE block_expr")
    def rest_if(self, p):
        return p.block_expr

    # async/await

    @_("ASYNC expr")
    def expr(self, p):
        return nodes.N_Async(p.expr)

    @_("AWAIT expr")
    def expr(self, p):
        return nodes.N_Await(p.expr)

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

    @_("SYMBOL")
    def expr(self, p):
        return nodes.N_Symbol(p.SYMBOL)

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

    def error(self, p):
        print(
            f'{getattr(p,"lineno","")}: ' f'Syntax error at {getattr(p,"value","EOC")}'
        )


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
