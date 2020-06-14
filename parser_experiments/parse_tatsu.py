import pprint
import json
import tatsu
from tatsu.util import asjson

# https://github.com/neogeny/TatSu/blob/master/examples/g2e/python.ebnf


exprs = [
    "bla",
    "123",
    '"bla"',
    "123.45",
    "bla34_dsa",
    "bla(one)",
    "bar # foo\nbaz",
    "foo\n  bar",
    "foo bar\n  baz",
    "foo\n  bar\n    baz",
    "foo\n  bar\n  cow\n    baz",
]


tealg = r"""
@@grammar::TEAL

single_input
    =
    newline | simple_stmt | compound_stmt newline
    ;


statement = assignment | expr ;

assignment = id "=" expr ;

expr = _exp0 ;

_exp0  = _nexp0 | _lexp0 | _rexp0;
_lexp0 = _exp1 ( _op_l0 _exp1 )*;
_nexp0 = _exp1 _op_n0 _exp1;
_rexp0 = ( _exp1 _op_r0 )* _exp1;
_op_l0 = "*" | "|";
_op_n0 = null;
_op_r0 = null;
_exp1  = _nexp1 | _lexp1 | _rexp1;
_lexp1 = _exp2 ( _op_l1 _exp2 )*;
_nexp1 = _exp2 _op_n1 _exp2;
_rexp1 = ( _exp2 _op_r1 )* _exp2;
_op_l1 = "+" | "-";
_op_n1 = null;
_op_r1 = null;
_exp2  = _nexp2 | _lexp2 | _rexp2;
_lexp2 = _exp3 ( _op_l2 _exp3 )*;
_nexp2 = _exp3 _op_n2 _exp3;
_rexp2 = ( _exp3 _op_r2 )* _exp3;
_op_l2 = null;
_op_n2 = "==" | "!=";
_op_r2 = null;
_exp3  = _nexp3 | _lexp3 | _rexp3;
_lexp3 = _exp4 ( _op_l3 _exp4 )*;
_nexp3 = _exp4 _op_n3 _exp4;
_rexp3 = ( _exp4 _op_r3 )* _exp4;
_op_l3 = null;
_op_n3 = null;
_op_r3 = "||" | "&&";


"""


tests = [
    "foo",
    # "foo()",
    # "1 + 2",
    # "1 * 2 + 3",
    # "1 * (2 + 3)",
    # "1 + (foo() + 4)",
]


def parse():
    for t in tests:
        print("---")
        print(t)
        print(":")
        ast = tatsu.parse(tealg, t)
        pprint.pprint(ast, indent=2, width=40)


if __name__ == "__main__":
    parse()
