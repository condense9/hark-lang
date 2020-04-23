import lark
from lark.indenter import Indenter


# https://docs.python.org/3/reference/lexical_analysis.html#indentation
class C9Indenter(Indenter):
    NL_type = "_NEWLINE"
    OPEN_PAREN_types = ["LPAR", "LSQB", "LBRACE"]
    CLOSE_PAREN_types = ["RPAR", "RSQB", "RBRACE"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4  # replaces tabs with this many spaces


def make_parser(*, start="start"):
    return lark.Lark.open(
        "c9_func.lark", parser="lalr", start=start, postlex=C9Indenter()
    )
