from parsimonious.utils import Token
from parsimonious import Grammar, TokenGrammar, NodeVisitor

# https://github.com/erikrose/parsimonious/issues/67



tealg = r"""
file = top_obj*
top_obj = (import / task / nl)

import = "importpy id "from" id ("as" id)? nl

task = "task" id "(" id* ")" block

block = ":" nl indent exprs dedent

exprs = (expr nl)*

expr =


nl = "NL"
indent = "INDENT"
dedent = "DEDENT"

id = ~"[a-z][a-z0-9_?]*"i
"""




tokens = r"""
stream = tok*
tok = (indent / notws / ws / nl / comment)

indent = ~r"^\s+"m

comment = ~"#.*"
nl = ~r"[\r\n]+"
ws = ~r"[ \t]+"

notws = ~r"[^#\s]+"
"""


# id = ~"[a-z][a-z0-9_?]*"i
# literal = number / string
# number = ~r"[0-9\.]+"
# string = ~'"[^\"]+"'
# symbol = ~r"[\[\]\(\)+-*/]


exprs = [
    "bla",
    "123",
    "123.45",
    "bla34_dsa",
    "bla(one)",
    "bar # foo\nbaz",
    "foo\n  bar",
    "foo bar\n  baz",
    "foo\n  bar\n    baz",
    "foo\n  bar\n  cow\n    baz",
]


# class String(Token)
# class Int(Token)
# class Float(Token)

class Indent(Token):
    def __init__(self):
        super().__init__("INDENT")

class Dedent(Token):
    def __init__(self):
        super().__init__("DEDENT")

class TV(NodeVisitor):
    """Return a stream of tokens"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._level = 0
        self._size = 0

    def visit_stream(self, node, visited_children):
        dedents = [Dedent()]*self._level
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
        return Token(type=node.match.group())

    def visit_tok(self, node, visited_children):
        return visited_children[0]

    def visit_nl(self, node, visited_children):
        return Token(type="NL")

    def visit_ws(self, node, visited_children):
        return None

    def visit_comment(self, node, visited_children):
        return None


if __name__ == "__main__":
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
