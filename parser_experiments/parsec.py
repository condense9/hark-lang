import re
from ast import literal_eval
from enum import Enum
from functools import lru_cache
from pprint import pprint
from typing import Any

import attr

from parsy import (
    ParseError,
    alt,
    digit,
    eof,
    from_enum,
    generate,
    match_item,
    regex,
    seq,
    string,
    string_from,
    test_item,
)

# https://www.attrs.org/en/stable/overview.html


@attr.s(auto_attribs=True)
class Linestart:
    spaces: str


class Indent:
    pass


class Dedent:
    pass


class Newline:
    pass


@attr.s(auto_attribs=True)
class Literal:
    value: Any


@attr.s(auto_attribs=True)
class Identifier:
    value: Any


@attr.s(auto_attribs=True)
# class Keyword:
#     name: str


class Op(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    SET = "="
    EQ = "=="
    NEQ = "!="
    AND = "&&"
    OR = "||"
    # DOT = "." # TODO?


# utils
exclude_none = lambda l: [i for i in l if i is not None]

# shared
ws = regex(r"[ \t]*")
nl = regex(r"[\r\n]+").result(Newline)

# keywords = ["def", "importpy", "if", "elif", "else", "async", "await"]
# keyword = string_from(*keywords).map(Keyword).desc("Keyword")

identifier = regex("[a-z][a-z0-9_?]*", flags=re.I).map(Identifier).desc("Identifier")
symbol = regex(r"[\(\)\,:]")
operator = from_enum(Op).desc("Operator")

string_ = regex(r'"[^\"]+"').desc("string")
# blockstring = string('"""') >> regex(".*") << string('"""')

integer = digit.at_least(1).concat().desc("Integer")
float_ = (
    (digit.at_least(1) + string(".").result(["."]) + digit.many()).concat()
    | (digit.many() + string(".").result(["."]) + digit.at_least(1)).concat()
).desc("Float")

number = float_ | integer
signed_number = (
    (string("-").optional().map(lambda x: x or "") + number).concat().map(literal_eval)
)

literal = (signed_number | string_).map(Literal)


def lex(text):
    comment = regex("#.*")
    linestart = regex(r"^\s+", flags=re.M).map(Linestart)
    tok_inner = literal | identifier | operator | symbol

    token = linestart | (ws >> tok_inner << ws) | nl | comment.result(None)
    tokens = token.many().map(exclude_none)

    return tokens.parse(text)


def post(toks):
    level = 0
    size = 0
    for t in toks:
        if isinstance(t, Linestart):
            if len(t.spaces) > size:
                size = len(t.spaces)
                level += 1
                yield Indent
            elif len(t.spaces) < size:
                size = len(t.spaces)
                level -= 1
                yield Dedent
        else:
            yield t

    while level > 0:
        yield Dedent(level)
        level -= 1


exprs = [
    "bla",
    "123",
    '"bla"',
    "123.45",
    "-5",
    "bla34_dsa",
    "bar # foo\nbaz",
    "def foo:\n  bar",
    "foo   bar\n  baz",
    "foo\n  bar\n    baz",
    "foo\n  bar\n  cow\n    baz",
]


def do_lex(s):
    return list(post(lex(s)))


def testlex():
    for expr in exprs:
        print("---")
        print(expr)
        print(":")
        toks = post(lex(expr))
        pprint(list(toks), indent=2, width=20)


## Now parse


@attr.s(auto_attribs=True)
class Infix:
    lhs: Any
    op: str
    rhs: Any


@attr.s(auto_attribs=True)
class Call:
    fn: str
    args: list


def ist(cls):
    # isinstance is slow
    return test_item(lambda x: type(x) == cls, cls)


# fmt: off
ops = [
    # Highest priority first
    # left-assoc,       non-assoc,       right-assoc
    [[Op.MUL, Op.DIV ], [],              []       ],
    [[Op.ADD, Op.SUB ], [],              []       ],
    [[               ], [Op.EQ, Op.NEQ], []       ],
    [[               ], [],              [Op.AND] ],
    [[               ], [],              [Op.OR]  ],
]
# fmt: on

# make a recursive parser expr parser builder

# https://github.com/condense9/teal-lang/blob/281a5f79c29d1a64e8ee4cbc9d7dc5b42cbdcc12/scratch/parser/funcish/c9_func.lark#L56
def build_expression_parser(table, term):
    @lru_cache
    def _exp(i):
        if i == len(table):
            p = term
        else:
            # The order is important. non-associative comes first (and must be
            # binary). Right associative is right-recursive and so comes next.
            # Finally, left associative (which also includes the base case to
            # terminate the recursion) comes last.
            p = (
                seq(_exp(i + 1), _qop("n", i), _exp(i + 1)).combine(Infix)
                # | _rexp(i)
                | _lexp(i)
            )
        return p

    @lru_cache
    def _rexp(i):
        higher_exp = _exp(i + 1)
        this_op = _qop("r", i)

        @generate
        def _genr():
            p = seq(higher_exp, this_op, (_rexp(i) | higher_exp)).combine(Infix)
            return (yield p)

        return _genr

    @lru_cache
    def _lexp(i):
        higher_exp = _exp(i + 1)
        this_op = _qop("l", i).optional()

        @generate
        def _genl():
            lhs = yield higher_exp
            while True:
                op = yield this_op
                if not op:
                    break
                rhs = yield higher_exp
                lhs = Infix(lhs, op, rhs)
            return lhs

        return _genl

    @lru_cache
    def _qop(a, i):
        col = {"l": 0, "n": 1, "r": 2}[a]
        # table is reversed order, highest priority first
        i = len(table) - i - 1
        if table[i][col]:
            return alt(*map(match_item, table[i][col]))
        else:
            # This should never match, but parsy doesn't have a null combinator
            return string("NOTHING")

    return _exp(0)


t_lpar = match_item("(")
t_rpar = match_item(")")
t_comma = match_item(",")
t_colon = match_item(":")

t_nl = match_item(Newline)
t_indent = match_item(Indent)
t_dedent = match_item(Dedent)

t_identifier = ist(Identifier)
t_literal = ist(Literal)


def t_kw(name):
    return test_item(
        lambda x: isinstance(x, Keyword) and x.name == name, f"Keyword {name}"
    )


@generate
def term():
    return (yield sub | fcall | t_identifier | t_literal)


expr = build_expression_parser(ops, term)

tup = t_lpar >> expr.sep_by(t_comma) << t_rpar
fcall = seq(t_identifier, tup).combine(Call)

sub = t_lpar >> expr << t_rpar


block = t_colon >> t_indent >> (expr << nl).many() << t_dedent

body = block | (expr << nl)

importpy = t_kw("importpy") >> t_identifier
arglist = t_identifier.sep_by(t_comma)
define = seq(t_kw("def") >> t_identifier, arglist, body)

statement = define | importpy

teal_file = (t_nl.many() >> statement << t_nl.many()).many()


# def parse_file(stream):
#     # task = string("task") >> ws >> identifier >> indent

#     binop1 = string("+")

#     atom = literal | identifier

#     @generate
#     def expr():
#         return (yield atom | expr + binop1 + expr | expr + binop2 + expr)

#     return expr.parse(stream)


tests = [
    "foo",
    "foo()",
    # "foo(1, 2)",
    # "1 + 2",
    # "1 + 2 + 3",
    # "1 * 2 + 3",
    # "1 * (2 + 3)",
    # "1 + (foo() + 4)",
]


def testparse():
    for t in tests:
        print("---")
        print(t)
        print(":")
        nodes = parse_file(t)
        pprint(nodes, indent=2, width=20)


# def compile():


if __name__ == "__main__":
    # testlex()
    testparse()
