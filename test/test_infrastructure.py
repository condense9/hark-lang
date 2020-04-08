import pytest

from c9 import compiler
from c9.lang import *
from c9.stdlib.http import HttpHandler


@HttpHandler("GET", "/foo")
def main(x):
    return 1


def test_foo():
    assert len(compiler.compile_function(main)) == 3  # bind, push, return

    res = compiler.get_resources(main)
    assert len(res) == 1  # GET__foo

    e = list(res)[0]
    assert e.method == "GET"
    assert e.path == "/foo"
    assert e.handler == "main"
