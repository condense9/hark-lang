"""Test the expression parser"""

import pytest
from c9.c9parser.evaluate import evaluate_exp

EXPR_TESTS = [
    "1",
    "2.0",
    '"foo"',
    "true",
    "false",
    "nil",
    "symb",
    "'symb",
    "'(g a)",
    "(g a)",
    # '{1 2 3 "b"}',
    # -- specials:
    "(if a 1 2)",
    "(if (f x) 1 (do 1 2))",
    "(let ((x 1) (y 2)) x)",
]


@pytest.mark.parametrize("expr", EXPR_TESTS)
def test_no_error(expr):
    """Test that expression parses without errors"""
    print(evaluate_exp(expr).code)


# TODO test the result is correct
