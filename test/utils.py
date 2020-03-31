"""Shared test utilities"""

import warnings
from typing import Dict, List

import c9c.compiler as compiler
import c9c.lang as l
import c9c.machine as m


def listing(code):
    print("\n".join(f"{i} | {a}" for i, a in enumerate(code)))


def list_defs(defs):
    for n, c in defs.items():
        print(f"{n}:")
        listing(c)


def check_compile_node(node, expected):
    """Check that the evaluation output is as expected"""
    result = [str(a) for a in compiler.compile_node(node).code]
    expected = [a.strip() for a in expected.split("\n")]
    expected = list(filter(lambda x: len(x), expected))  # Remove empty lines
    assert len(expected) == len(result)
    for i, (a, b) in enumerate(zip(result, expected)):
        assert i >= 0 and a.strip() == b.strip()


def check_compile_all(fn: l.Func, expected: Dict, allow_custom_validation=False):
    """Check that some function definitions are correct"""
    defs = compiler.compile_all(fn)
    for k in expected.keys():
        assert k in defs
        assert len(defs[k]) == len(expected[k])
        for i, (a, b) in enumerate(zip(defs[k], expected[k])):
            if not isinstance(b, l.Node) and callable(b):
                if allow_custom_validation:
                    assert b(a)
                else:
                    raise Exception("Custom validation disabled")
            else:
                assert k and i >= 0 and a == b
