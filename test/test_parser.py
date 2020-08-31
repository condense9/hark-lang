from pathlib import Path
import pytest

from hark_lang.hark_parser import parser, nodes


@pytest.mark.parametrize(
    "test_case, source, op",
    [
        ("/binop/add", "x + 1", "+"),
        ("/binop/sub", "x - 1", "-"),
        ("/binop/mul", "x * 1", "*"),
        ("/binop/div", "x / 1", "/"),
        ("/binop/mod", "x % 1", "%"),
        ("/binop/gt", "x > 1", ">"),
        ("/binop/lt", "x < 1", "<"),
        ("/binop/gte", "x >= 1", ">="),
        ("/binop/lte", "x <= 1", "<="),
        ("/binop/eq", "x == 1", "=="),
        ("/binop/neq", "x != 1", "!="),
        ("/binop/and", "x && 1", "&&"),
        ("/binop/or", "x || 1", "||"),
    ],
)
def test_binop(test_case, source, op):
    ast, *rest = parser.tl_parse(test_case, source)
    assert not rest
    assert ast.lhs.name == "x"
    assert ast.op == op
    assert ast.rhs.value == 1


@pytest.mark.parametrize(
    "test_case, source, op",
    [
        ("/unaryop/neg", "-1", "-"),
        ("/unaryop/neg", "-x", "-"),
        ("/unaryop/await", "- await foo(1, 2, 3)", "-"),
        ("/unaryop/async", "async (- foo(1, 2, 3) + 1)", "async"),
        ("/unaryop/not", "!await (foo(1) + 1)", "!"),
    ],
)
def test_unaryop(test_case, source, op):
    ast, *rest = parser.tl_parse(test_case, source)
    assert not rest
    assert ast.op == op


def examples(root=None):
    root: Path = (root or Path(".")).absolute()
    # TODO: find a better way of using existing hark code
    yield from root.glob("**/examples/*.hk")


@pytest.mark.parametrize(
    "source_file", (p for p in examples() if p.name != "bad_syntax.hk")
)
def test_successful_code(source_file):
    with open(source_file) as f:
        ast = parser.tl_parse(source_file, f.read())


def test_bad_syntax():
    bad_syntax = next(p for p in examples() if p.name == "bad_syntax.hk")
    with open(bad_syntax) as f, pytest.raises(parser.HarkParseError):
        parser.tl_parse(bad_syntax, f.read())
