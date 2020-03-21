"""Test that the compiler generates appropriate machine code"""

import compiler
import lang as l
import machine as m
from lang import Foreign, Func
from simple_functions import *
from stdlib import Map
from utils import check_compile_all, check_compile_node, list_defs, listing

################################################################################
## Test nodes first


@Func
def dummy(a, b):
    return a


def test_dummy():
    node = l.Symbol(1)
    check_compile_node(node, "PUSHB    1")


def test_value():
    node = l.Quote(4)
    check_compile_node(node, "PUSHV    4")


def test_simple_if():
    c = l.Quote(True)
    a = l.Quote(1)
    b = l.Quote(2)
    node = l.If(c, a, b)
    check_compile_node(
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
    check_compile_node(
        node,
        """
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        CALL
        PUSHV    True
        JUMPIE   2
        PUSHV    2
        JUMP     1
        PUSHV    True
        """,
    )


def test_apply():
    node = l.Funcall(dummy, l.Quote(1), l.Quote(2))
    check_compile_node(
        node,
        """
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        CALL
        """,
    )


def test_apply2():
    result = l.Funcall(dummy, l.Quote(1), l.Quote(2))
    node = l.Funcall(dummy, result, l.Quote(3))
    check_compile_node(
        node,
        """
        PUSHV    3
        PUSHV    2
        PUSHV    1
        PUSHV    F_dummy
        CALL
        PUSHV    F_dummy
        CALL
        """,
    )


def test_builtin():
    node = l.Cons(l.Quote(0), l.Quote(1))
    check_compile_node(
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
    check_compile_all(
        simple_func2,
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
                m.Call(),
                m.Return()
                # --
            ],
        },
    )


@Func
def fcall_times2(a):
    return l.ForeignCall(times2, a)


def test_fcall():
    check_compile_all(
        fcall_times2,
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
    node = l.Funcall(Map, fcall_times2, l.Quote([1, 2, 3]))
    listing(compiler.compile_node(node).code)


def test_call_map():
    check_compile_all(
        Map,
        {
            "F_Map": [
                m.Bind(0),
                m.Bind(1),
                m.PushB(1),
                l.Nullp,
                m.PushV(True),
                m.JumpIE(11),
                m.PushB(1),
                l.First,
                m.PushB(0),
                m.Call(),
                m.PushB(1),
                l.Rest,
                m.PushB(0),
                m.PushV("F_Map"),
                m.Call(),
                l.Cons,
                m.Jump(1),
                m.PushV([]),
                m.Return(),
            ]
        },
    )


@Func
def simple_map(a):
    return Map(fcall_times2, a)


def test_map():
    check_compile_all(
        simple_map,
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
                m.PushV(Map.label),
                m.Call(),
                m.Return()
                # --
            ],
        },
    )


@Foreign
def simple_math(x):
    return x - 1


@Func
def call_foreign(x):
    return simple_math(x)


def test_foreign():
    check_compile_all(
        call_foreign,
        {
            # It's hard to test the MFCall, as the function it's calling is an
            # instance method. But here's what it looks like:
            #
            # "FF_simple_math": [
            #     # --
            #     m.Bind(0),
            #     m.PushB(0),
            #     m.Wait(),
            #     lambda x: (x.operands[1] == 1 and x.operands[0] is l.Foreign._wrapper),
            #     m.Return()
            #     # --
            # ],
            "F_call_foreign": [
                # --
                m.Bind(0),
                m.PushB(0),
                m.PushV("FF_simple_math"),
                m.Call(),
                m.Return()
                # --
            ],
        },
    )


def test_link():
    @Func
    def main(a):
        return a

    compiled = compiler.compile_all(main)
    linked = compiler.link(compiled)
    assert "F_main" in linked.locations
    # The linker should add some code:
    assert len(linked.code) > sum(len(code) for code in compiled.values())


if __name__ == "__main__":
    # print(compile_function(simple_func2))
    # list_defs(compile_all(simple_func2))
    # test_func_if()
    # test_compile_all()
    # test_fcall()
    # compile_all(simple_map)
    test_compile_all()
