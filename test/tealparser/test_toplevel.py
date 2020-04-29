"""Test the file parser"""

import pytest
from teal.tealparser.evaluate import evaluate_toplevel


FILE_TESTS = [
    # --
    "(def f (x y) (print x) x)",
    '(def main () "hello world")',
    """
(def f (x y) (print x) x)
(def g (x) (f x x))
    """,
]


@pytest.mark.parametrize("content", FILE_TESTS)
def test_no_error(content):
    """Test that toplevel content evaluates without errors"""
    result = evaluate_toplevel(content)
    print(result.defs)
    print(result.foreigns)


# TODO test the result is correct
