import os
from ast import literal_eval
from typing import Any
from itertools import chain

from sly import Lexer, Parser
from sly.lex import Token

from . import nodes


class TealSyntaxError(Exception):
    def __init__(self, token, msg):
        self.token = token
        self.msg = msg


class TealLexer(Lexer):
    tokens = {
        ATTRIBUTE,
        TERM,
        SYMBOL,
        ID,
        # keywords
        FN,
        LAMBDA,
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
        NULL,
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
    literals = {"(", ")", ",", "{", "}", "[", "]", ":"}

    ignore = " \t"

    @_(r"#\[.*\]\n")
    def ATTRIBUTE(self, t):
        return t

    # Must come before DIV (same starting char)
    @_(r"(/\*(.|\n)*?\*/)|(//.*)")
    def COMMENT(self, t):
        t.lineno += t.value.count("\n")

    # Not a token used by parsing, but used in post_lex as an alternative
    # terminator.
    @_(r"\n+")
    def NL(self, t):
        self.lineno = t.lineno + t.value.count("\n")
        return t

    # Identifiers and keywords
    ID = "[a-z_][a-zA-Z0-9_?.]*"
    ID["fn"] = FN
    ID["lambda"] = LAMBDA
    ID["if"] = IF
    ID["elif"] = ELIF
    ID["else"] = ELSE
    ID["async"] = ASYNC
    ID["await"] = AWAIT
    ID["true"] = TRUE
    ID["false"] = FALSE
    ID["null"] = NULL

    SYMBOL = r":[a-z][a-zA-Z0-9_]*"

    # values
    NUMBER = r"[+-]?[\d]+[\d.]*"
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

    def error(self, t):
        raise TealSyntaxError(t, f"Illegal character `{t.value[0]}`")


def post_lex(toks):
    # Add the optional terminators after lines/blocks
    term = Token()
    term.value = ";"
    term.type = "TERM"
    nl = Token()
    nl.type = "NL"

    t = next(toks)
    last = None
    for next_tok in chain(toks, [nl]):
        if t.type != "NL":
            yield t
            last = t

        term.lineno = t.lineno
        term.index = t.index

        if last and last.type != "TERM":
            if (
                (t.type == "}" and next_tok.type != "TERM")
                or (next_tok.type == "}" and t.type != "TERM")
                or (next_tok.type == "NL" and t.type != "TERM")
            ):
                yield term
                last = term

        t = next_tok


### PARSER


class TealParser(Parser):
    # debugfile = "parser.out"
    tokens = TealLexer.tokens
    precedence = (
        ("nonassoc", LT, GT),
        ("right", OR),
        ("right", AND),
        ("nonassoc", EQ, SET),
        ("left", ADD, SUB),
        ("left", MUL, DIV),
        ("right", AWAIT),
        ("right", "("),
        ("right", ASYNC),
    )

    start = "top"

    @_("")
    def nothing(self, p):
        pass

    # blocks

    @_("'{' expressions '}'")
    def block_expr(self, p):
        if not p.expressions:
            # TODO parser error framework
            raise Exception("Empty block expression")
        return nodes.N_Progn(p.index, p.expressions)

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

    @_("maybe_attribute FN ID '(' paramlist ')' block_expr")
    def expr(self, p):
        return nodes.N_Definition(
            p.index, p.ID, p.paramlist, p.block_expr, p.maybe_attribute
        )

    @_("nothing")
    def maybe_attribute(self, p):
        return None

    @_("ATTRIBUTE")
    def maybe_attribute(self, p):
        return p.ATTRIBUTE

    @_("LAMBDA '(' paramlist ')' block_expr")
    def expr(self, p):
        return nodes.N_Lambda(p.index, p.paramlist, p.block_expr)

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

    # NOTE: to avoid a conflict between "LAMBDA (" and "expr (", function calls
    # are restricted to "named" calls - ie you can't directly call the result of
    # an expression, you have to assign to a variable first. This isn't ideal,
    # but too hard to fix now.

    # NOTE:
    @_("ID '(' arglist ')'")
    def expr(self, p):
        return nodes.N_Call(p.index, nodes.N_Id(p.index, p.ID), p.arglist)

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
        return nodes.N_Argument(None, None, p.expr)

    @_("SYMBOL expr")
    def arg_item(self, p):
        # named arguments.
        # A bit icky - conflicts with SYMBOL
        return nodes.N_Argument(p.index, nodes.N_Symbol(p.index, p.SYMBOL), p.expr)

    # sub

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    # conditional

    @_("IF expr block_expr TERM rest_if")
    def expr(self, p):
        return nodes.N_If(p.index, p.expr, p.block_expr, p.rest_if)

    @_("ELIF expr block_expr TERM rest_if")
    def rest_if(self, p):
        return nodes.N_If(p.index, p.expr, p.block_expr, p.rest_if)

    @_("ELSE block_expr")
    def rest_if(self, p):
        return p.block_expr

    # async/await

    @_("ASYNC expr")
    def expr(self, p):
        return nodes.N_Async(p.index, p.expr)

    @_("AWAIT expr")
    def expr(self, p):
        return nodes.N_Await(p.index, p.expr)

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
        return nodes.N_Binop(p.index, p[0], p[1], p[2])

    # compound

    @_("'[' maybe_term list_items maybe_term ']'")
    def expr(self, p):
        return nodes.N_Call(p.index, nodes.N_Id(p.index, "list"), p.list_items)

    @_("nothing")
    def list_items(self, p):
        return []

    @_("expr")
    def list_items(self, p):
        return [p.expr]

    @_("expr ',' maybe_term list_items")
    def list_items(self, p):
        return [p.expr] + p.list_items

    @_("'{' maybe_term dict_items maybe_term '}'")
    def expr(self, p):
        return nodes.N_Call(p.index, nodes.N_Id(p.index, "hash"), p.dict_items)

    # TODO fix, this is icky - TERM can either be ';' or '\n'
    @_("nothing")
    def dict_items(self, p):
        return []

    @_("expr ':' expr maybe_term")
    def dict_items(self, p):
        return [p[0], p[2]]

    @_("expr ':' expr maybe_term ',' maybe_term dict_items")
    def dict_items(self, p):
        return [p[0], p[2]] + p.dict_items

    @_("nothing", "TERM")
    def maybe_term(self, p):
        pass

    # literals

    @_("ID")
    def expr(self, p):
        return nodes.N_Id(p.index, p.ID)

    @_("SYMBOL")
    def expr(self, p):
        return nodes.N_Symbol(p.index, p.SYMBOL)

    @_("TRUE")
    def expr(self, p):
        return nodes.N_Literal(p.index, True)

    @_("FALSE")
    def expr(self, p):
        return nodes.N_Literal(p.index, False)

    @_("NULL")
    def expr(self, p):
        return nodes.N_Literal(p.index, None)

    @_("NUMBER")
    def expr(self, p):
        return nodes.N_Literal(p.index, literal_eval(p.NUMBER))

    @_("STRING")
    def expr(self, p):
        return nodes.N_Literal(p.index, literal_eval(p.STRING))

    def error(self, p):
        raise TealSyntaxError(p, f"Unexpected token `{p.value}`")


###


def token_column(text, index):
    """Compute column position of token in text"""
    last_cr = text.rfind("\n", 0, index)
    if last_cr < 0:
        last_cr = 0
    column = (index - last_cr) + 1
    return column


def tl_parse(text, debug_lex=False):
    parser = TealParser()
    lexer = TealLexer()
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
