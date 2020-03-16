import warnings
from compiler import *
from typing import Dict, List

import lang as l
import machine as m
from lang import Func
from simple_functions import *


def listing(code):
    print("\n".join(f"{i} | {a}" for i, a in enumerate(code)))


def list_defs(defs):
    for n, c in defs.items():
        print(f"{n}:")
        listing(c)


def check(node, expected):
    """Check that the evaluation output is as expected"""
    result = [str(a) for a in compile_node(node).code]
    expected = [a.strip() for a in expected.split("\n")]
    expected = list(filter(lambda x: len(x), expected))
    assert len(expected) == len(result)
    for i, (a, b) in enumerate(zip(result, expected)):
        assert i >= 0 and a.strip() == b.strip()


def check_compiled(defs: Dict[str, List[m.Instruction]], expected):
    """Check that some function definitions are correct"""
    for k in defs.keys():
        if k not in expected:
            warnings.warn(f"Not checking definition of {k}")
    for k in expected.keys():
        assert k in defs
        assert len(defs[k]) == len(expected[k])
        for i, (a, b) in enumerate(zip(defs[k], expected[k])):
            # Awkward. Builtins take arguments in the source, but not in the
            # assembly. So this is to avoid having to instantiate real builtins
            # in EXPECTED
            if isinstance(a, l.Builtin):
                assert k and i >= 0 and type(a) == b
            else:
                assert k and i >= 0 and a == b


################################################################################
## Test nodes first


@Func
def dummy(a, b):
    return a


def test_dummy():
    node = Symbol(1)
    check(node, "PUSHB    1")


def test_value():
    node = l.Quote(4)
    check(node, "PUSHV    4")


def test_simple_if():
    c = l.Quote(True)
    a = l.Quote(1)
    b = l.Quote(2)
    node = l.If(c, a, b)
    check(
        node,
        """
        PUSHV    True
        PUSHV    True
        JUMPIE   2
        PUSHV    2
        JUMP     1
        PUSHV    1
        """,
    )


def test_func_if():
    # Try switching the order to check:
    a = l.Quote(True)
    c = l.Funcall(dummy, l.Quote(1), l.Quote(2))
    b = l.Quote(2)
    node = l.If(c, a, b)
    check(
        node,
        """
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        $FUNCALL
        PUSHV    True
        JUMPIE   2
        PUSHV    2
        JUMP     1
        PUSHV    True
        """,
    )


def test_apply():
    node = l.Funcall(dummy, l.Quote(1), l.Quote(2))
    check(
        node,
        """
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        $FUNCALL
        """,
    )


def test_apply2():
    result = l.Funcall(dummy, l.Quote(1), l.Quote(2))
    node = l.Funcall(dummy, result, l.Quote(3))
    check(
        node,
        """
        PUSHV    3
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        $FUNCALL
        PUSHV    F_dummy
        $FUNCALL
        """,
    )


def test_builtin():
    node = l.Cons(l.Quote(0), l.Quote(1))
    check(
        node,
        """
        PUSHV    0
        PUSHV    1
        $CONS
        """,
    )


################################################################################
## Now functions!


@Func
def simple_func(a, b):
    return a


@Func
def simple_func2(a):
    return simple_func(a, a)


def test_compile_all():
    defs = compile_all(simple_func2)
    check_compiled(
        defs,
        {
            "F_simple_func": [
                # --
                m.Bind(0),
                m.Bind(1),
                m.PushB(0),
                m.Return()
                # --
            ],
            "F_simple_func2": [
                # --
                m.Bind(0),
                m.PushB(0),
                m.PushB(0),
                m.PushV("F_simple_func"),
                l.Funcall,
                m.Return()
                # --
            ],
        },
    )


@Func
def fcall_times2(a):
    return l.FCall(times2, a)


def test_fcall():
    defs = compile_all(fcall_times2)
    check_compiled(
        defs,
        {
            fcall_times2.label: [
                # --
                m.Bind(0),
                m.PushB(0),
                m.Wait(),
                m.MFCall(times2, 1),
                m.Return()
                # --
            ]
        },
    )


def test_apply_map():
    node = l.Funcall(l.Map, fcall_times2, l.Quote([1, 2, 3]))
    listing(compile_node(node).code)


def test_call_map():
    defs = compile_all(l.Map)
    check_compiled(
        defs,
        {
            "F_Map": [
                m.Bind(0),
                m.Bind(1),
                m.PushB(1),
                l.Nullp,
                m.PushV(True),
                m.JumpIE(11),
                m.PushB(1),
                l.Car,
                m.PushB(0),
                l.Funcall,
                m.PushB(1),
                l.Cdr,
                m.PushB(0),
                m.PushV("F_Map"),
                l.Funcall,
                l.Cons,
                m.Jump(1),
                m.PushV([]),
                m.Return(),
            ]
        },
    )


@Func
def simple_map(a):
    return l.Map(fcall_times2, a)


def test_map():
    defs = compile_all(simple_map)
    check_compiled(
        defs,
        {
            fcall_times2.label: [
                # --
                m.Bind(0),
                m.PushB(0),
                m.Wait(),
                m.MFCall(times2, 1),
                m.Return()
                # --
            ],
            simple_map.label: [
                # --
                m.Bind(0),
                m.PushB(0),
                m.PushV(fcall_times2.label),
                m.PushV(l.Map.label),
                l.Funcall,
                m.Return()
                # --
            ],
        },
    )


if __name__ == "__main__":
    # print(compile_function(simple_func2))
    # list_defs(compile_all(simple_func2))
    # test_func_if()
    # test_compile_all()
    # test_fcall()
    # compile_all(simple_map)
    test_compile_all()
