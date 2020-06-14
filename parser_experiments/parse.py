import pprint

import teal_ops
from parsimonious import Grammar, NodeVisitor, TokenGrammar
from parsimonious.utils import Token

# https://github.com/erikrose/parsimonious/issues/67
# https://docs.python.org/3/reference/grammar.html


tokens = r"""
stream = tok*
tok = (indent / notws / ws / nl / comment)

indent = ~r"^\s+"m

comment = ~"#.*"
nl = ~r"[\r\n]+"
ws = ~r"[ \t]+"

notws = id / number / string / symbol

id = ~"[a-z][a-z0-9_?]*"i
number = ~r"-?[0-9\.]+"
string = ~'"[^\"]+"'
symbol = ~r"[\[\]\(\)-*/\.\+,]"
"""


exprs = [
    "bla",
    "123",
    '"bla"',
    "123.45",
    "-5",
    "bla34_dsa",
    "bla(one)",
    "bar # foo\nbaz",
    "foo\n  bar",
    "foo bar\n  baz",
    "foo\n  bar\n    baz",
    "foo\n  bar\n  cow\n    baz",
]


class Indent(Token):
    def __init__(self):
        super().__init__("INDENT")


class Dedent(Token):
    def __init__(self):
        super().__init__("DEDENT")


class Identifier(Token):
    def __init__(self, label):
        self.label = label
        super().__init__("ID")

    def __repr__(self):
        return f"<Identifier {self.label}>"


class Number(Token):
    def __init__(self, value):
        self.value = value
        super().__init__("NUMBER")

    def __repr__(self):
        return f"<Number {self.value}>"


class String(Token):
    def __init__(self, value):
        self.value = value
        super().__init__("STRING")

    def __repr__(self):
        return f"<String {self.value}>"


class TV(NodeVisitor):
    """Return a stream of tokens"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._level = 0
        self._size = 0

    def visit_stream(self, node, visited_children):
        dedents = [Dedent()] * self._level
        return list(filter(None, visited_children + dedents + [Token(type="EOF")]))

    def visit_indent(self, node, visited_children):
        size = len(node.match.group())
        if size > self._size:
            self._size = size
            self._level += 1
            return Indent()
        elif size < self._size:
            self._size = size
            self._level -= 1
            return Dedent()

    def visit_notws(self, node, visited_children):
        return visited_children[0]

    def visit_id(self, node, visited_children):
        return Identifier(node.match.group())

    def visit_number(self, node, visited_children):
        return Number(node.match.group())

    def visit_string(self, node, visited_children):
        return String(node.match.group())

    def visit_symbol(self, node, visited_children):
        return Token(type=node.match.group())

    def visit_tok(self, node, visited_children):
        return visited_children[0]

    def visit_nl(self, node, visited_children):
        return Token(type="NL")

    def visit_ws(self, node, visited_children):
        return None

    def visit_comment(self, node, visited_children):
        return None


def tokenise():
    # grammar = TokenGrammar(g1)
    tokenp = Grammar(tokens)

    for expr in exprs:
        tree = tokenp.parse(expr)
        vis = TV()
        print("---")
        print(expr)
        print(":")
        # print(tree)
        print(vis.visit(tree))


## Lexing done, now parsing:


tealg1 = r"""
start = (statement)* eof
statement = assignment / expr

assignment = id "=" expr


expr = exp1

exp1 = exp2 (op1 exp2)*
exp2 = atom (op2 atom)*
op1 = "+" / "-"
op2 = "*" / "/"


atom   = fcall / subexp / string / number / id
subexp = "(" expr ")"
fcall = id "(" (expr ("," expr)*)? ")"


eof = "EOF"
id = "ID"
number = "NUMBER"
string = "STRING"
nl = "NL"
indent = "INDENT"
dedent = "DEDENT"
"""


tealg = r"""
start = (statement)* eof
statement = assignment / expr

assignment = id "=" expr

expr = _exp0

# autogen
{}
# end

null = "NULL"
_exp4 = atom

atom   = fcall / subexp / string / number / id
subexp = "(" expr ")"
fcall = id "(" (expr ("," expr)*)? ")"


eof = "EOF"
id = "ID"
number = "NUMBER"
string = "STRING"
nl = "NL"
indent = "INDENT"
dedent = "DEDENT"
""".format(
    teal_ops.gen()
)

tests = [
    "foo",
    # "foo()",
    # "foo(1, 2)",
    # "1 + 2",
    # "1 + 2 + 3",
    # "1 * 2 + 3",
    # "1 * (2 + 3)",
    # "1 + (foo() + 4)",
]


class Flatten(NodeVisitor):
    def visit_start(self, node, visited_children):
        return list(filter(None, visited_children))

    def visit_statement(self, node, visited_children):
        return visited_children[0]

    def visit_eof(self, node, visited_children):
        return None

    def generic_visit(self, node, visited_children):
        if node.expr.name.startswith("_exp"):
            return list(filter(None, visited_children))
        if node.expr.name.startswith("_lexp"):
            return list(filter(None, visited_children))
        if hasattr(node, "members") and not node.members:
            return None
        return node


def parse():
    tokeniser = Grammar(tokens)
    parser = TokenGrammar(tealg)

    for t in tests:
        vis = TV()
        toks = vis.visit(tokeniser.parse(t))
        print("---")
        print(t)
        print(":")
        print(toks)
        print("=>")
        ast = parser.parse(toks)
        print(ast)
        flat = Flatten().visit(ast)
        pprint.pprint(flat, indent=2, width=20)


if __name__ == "__main__":
    parse()
