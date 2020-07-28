import os
import logging
from ast import literal_eval
from itertools import chain
from pathlib import Path
from typing import Any

from sly import Lexer, Parser
from sly.lex import Token

from ..cli.interface import format_source_problem
from ..exceptions import UserResolvableError
from . import nodes as n


class TealParseError(UserResolvableError):
    """Parse error"""

    def __init__(self, msg, filename, source_text, token):
        source_line = source_text.split("\n")[token.lineno - 1]
        source_column = index_column(source_text, token.index)
        explanation = format_source_problem(
            filename, token.lineno, source_line, source_column,
        )
        super().__init__(msg, explanation)


def index_column(text, index):
    """Compute column position of a token index in text"""
    last_cr = text.rfind("\n", 0, index)
    if last_cr < 0:
        last_cr = 0
    column = index - last_cr
    return column


class TealLexer(Lexer):
    def __init__(self, filename, source_text):
        super().__init__()
        self.filename = filename
        self.source_text = source_text

    tokens = {
        TERM,
        ATTRIBUTE,
        SYMBOL,
        ID,
        # keywords
        FN,
        LAMBDA,
        IF,
        ELSE,
        ASYNC,
        AWAIT,
        TRUE,
        FALSE,
        # values
        NUMBER,
        STRING,
        SQ_STRING,
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
        self.lineno += t.value.count("\n")

    # Not a token used by parsing, but used in post_lex as an alternative
    # terminator.
    @_(r"\n+")
    def NL(self, t):
        self.lineno = t.lineno + t.value.count("\n")

    # Identifiers and keywords
    ID = "[a-z_][a-zA-Z0-9_?.]*"
    ID["fn"] = FN
    ID["lambda"] = LAMBDA
    ID["if"] = IF
    ID["else"] = ELSE
    ID["async"] = ASYNC
    ID["await"] = AWAIT
    ID["true"] = TRUE
    ID["false"] = FALSE
    ID["null"] = NULL

    SYMBOL = r":[a-z][a-zA-Z0-9_]*"

    # values
    NUMBER = r"[+-]?[\d]+[\d.]*"
    STRING = r'"(?:[^"\\]|\\.)*"'
    SQ_STRING = r"'(?:[^'\\]|\\.)*'"

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
        raise TealParseError(
            f"Illegal character `{t.value[0]}`", self.filename, self.source_text, t
        )


def post_lex(toks):
    """Tweak the token stream to simplify the grammar"""
    term = Token()
    term.value = ";"
    term.type = "TERM"

    try:
        t = next(toks)
    except StopIteration:
        return []

    for next_tok in chain(toks, [term]):
        yield t

        term.lineno = t.lineno
        term.index = t.index

        # TERMs after blocks and after the last expression in a block are
        # optional. Fill them in here to make the grammar simpler.
        #
        # There are two places where '}' is used, and so there are two places
        # terminators must be consumed: block expressions and hashes.
        #
        # block: { a; b; c } -> { a; b; c; };
        #
        # hashes: { a: b, c: d } -> { a: b, c: d; };

        # Closing a block or hash
        if t.type == "}" and next_tok.type != ";":
            yield term

        # Last expression in a block or hash
        if next_tok.type == "}" and t.type != "TERM":
            yield term

        t = next_tok
    yield t


### PARSER


def N(parser, parse_item, node_cls: n.Node, *args):
    """Factory for nodes with source text line and column information"""
    try:
        lineno = parser.source_text[: parse_item.index].count("\n") + 1
        line = parser.source_text.split("\n")[lineno - 1]
        column = index_column(parser.source_text, parse_item.index)
    except AttributeError:
        lineno = None
        line = None
        column = None

    return node_cls(parser.filename, lineno, line, column, *args)


class TealParser(Parser):
    # debugfile = "parser.out"
    log = logging.getLogger(__name__)

    def __init__(self, filename, source_text):
        super().__init__()
        self.filename = filename
        self.source_text = source_text

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
        return N(
            self, p, n.N_Definition, p.ID, p.paramlist, p.block_expr, p.maybe_attribute,
        )

    @_("nothing")
    def maybe_attribute(self, p):
        return None

    @_("ATTRIBUTE")
    def maybe_attribute(self, p):
        return p.ATTRIBUTE

    @_("LAMBDA '(' paramlist ')' block_expr")
    def expr(self, p):
        return N(self, p, n.N_Lambda, p.paramlist, p.block_expr)

    @_("nothing")
    def paramlist(self, p):
        return []

    @_("ID")
    def paramlist(self, p):
        return [p.ID]

    @_("ID ',' paramlist")
    def paramlist(self, p):
        return [p.ID] + p.paramlist

    @_("'{' expressions '}'")
    def block_expr(self, p):
        if not p.expressions:
            # TODO parser error framework
            raise Exception("Empty block expression")
        return N(self, p, n.N_Progn, p.expressions)

    # function call

    # NOTE: to avoid a conflict between "LAMBDA (" and "expr (", function calls
    # are restricted to "named" calls - ie you can't directly call the result of
    # an expression, you have to assign to a variable first. This isn't ideal,
    # but too hard to fix now.

    # NOTE:
    @_("ID '(' arglist ')'")
    def expr(self, p):
        identifier = N(self, p, n.N_Id, p.ID)
        return N(self, p, n.N_Call, identifier, p.arglist)

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
        return N(self, p, n.N_Argument, None, p.expr)

    @_("SYMBOL expr")
    def arg_item(self, p):
        # named arguments.
        # A bit icky - conflicts with SYMBOL
        symbol = N(self, p, n.N_Symbol, p.SYMBOL)
        return N(self, p, n.N_Argument, symbol, p.expr)

    # sub

    @_("'(' expr ')'")
    def expr(self, p):
        return p.expr

    # conditional

    @_("IF expr block_expr TERM rest_if")
    def expr(self, p):
        return N(self, p, n.N_If, p.expr, p.block_expr, p.rest_if)

    @_("ELSE IF expr block_expr TERM rest_if")
    def rest_if(self, p):
        # Tail-call recursion expects the body of an if-expression to be a
        # Progn. It's much easier and cleaner to just wrap with an implicit
        # progn here, than to "fix" the tail-call recursion logic.
        body = N(self, p, n.N_If, p.expr, p.block_expr, p.rest_if)
        return N(self, p, n.N_Progn, [body])

    @_("ELSE block_expr")
    def rest_if(self, p):
        return p.block_expr

    @_("nothing")
    def rest_if(self, p):
        # p will be None, and won't have source info. Use the previous token
        # instead.
        p = self.symstack[-2]
        nothing = N(self, p, n.N_Literal, None)
        return N(self, p, n.N_Progn, [nothing])

    # async/await

    @_("ASYNC expr")
    def expr(self, p):
        return N(self, p, n.N_Async, p.expr)

    @_("AWAIT expr")
    def expr(self, p):
        return N(self, p, n.N_Await, p.expr)

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
        return N(self, p, n.N_Binop, p[0], p[1], p[2])

    # compound

    @_("'[' list_items ']'")
    def expr(self, p):
        identifier = N(self, p, n.N_Id, "list")  # list constructor
        return N(self, p, n.N_Call, identifier, p.list_items)

    @_("nothing")
    def list_items(self, p):
        return []

    @_("expr")
    def list_items(self, p):
        return [p.expr]

    @_("expr ',' list_items")
    def list_items(self, p):
        return [p.expr] + p.list_items

    @_("'{' hash_items TERM '}' TERM")
    def expr(self, p):
        identifier = N(self, p, n.N_Id, "hash")  # hash constructor
        return N(self, p, n.N_Call, identifier, p.hash_items)

    @_("nothing")
    def hash_items(self, p):
        return []

    @_("expr ':' expr")
    def hash_items(self, p):
        return [p[0], p[2]]

    @_("expr ':' expr ',' hash_items")
    def hash_items(self, p):
        return [p[0], p[2]] + p.hash_items

    # literals

    @_("ID")
    def expr(self, p):
        return N(self, p, n.N_Id, p.ID)

    @_("SYMBOL")
    def expr(self, p):
        return N(self, p, n.N_Symbol, p.SYMBOL)

    @_("TRUE")
    def expr(self, p):
        return N(self, p, n.N_Literal, True)

    @_("FALSE")
    def expr(self, p):
        return N(self, p, n.N_Literal, False)

    @_("NULL")
    def expr(self, p):
        return N(self, p, n.N_Literal, None)

    @_("NUMBER")
    def expr(self, p):
        return N(self, p, n.N_Literal, literal_eval(p.NUMBER))

    @_("STRING", "SQ_STRING")
    def expr(self, p):
        return N(self, p, n.N_Literal, literal_eval(p[0]))

    def error(self, p):
        raise TealParseError(
            f"Unexpected token `{p.value}`", self.filename, self.source_text, p
        )


###


def tl_parse(filename: str, text: str, debug_lex=False):
    filename = str(Path(filename).absolute().resolve())
    parser = TealParser(filename, text)
    lexer = TealLexer(filename, text)
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
