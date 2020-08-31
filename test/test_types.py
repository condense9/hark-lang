import pytest
import json

from hark_lang.machine.types import *


def to_json_and_back(obj: TlType):
    """Serialise an object to JSON and back"""
    ser = obj.serialise()
    jser = json.dumps(ser)
    jdeser = json.loads(jser)
    deser = TlType.deserialise(jdeser)
    return deser


def test_true():
    original = TlTrue()
    ser = original.serialise()
    deser = TlType.deserialise(ser)
    assert original == deser


def test_literals():
    int_a = TlInt(5)
    int_b = TlInt(3)
    int_c = TlInt(4)
    assert isinstance(int_a, int)
    assert int_a + int_b == 8
    ser = int_a.serialise()
    deser = TlType.deserialise(ser)
    assert deser + int_c == 9


def test_hashes():
    h = TlHash(
        {
            TlInt(1): TlInt(2),
            TlInt(3): TlInt(4),
            TlString("5"): TlList([TlInt(1), TlInt(31)]),
        }
    )
    deser = to_json_and_back(h)
    assert h == deser


def test_lists():
    inner = TlList([TlInt(1), TlInt(31)])
    l = TlList([TlInt(1), TlInt(31), TlString("bla"), inner])
    deser = to_json_and_back(l)
    assert l == deser


def test_list():
    list_a = TlList([TlInt(1), TlInt(2), TlInt(3)])
    assert len(list_a) == 3
    list_a.append(TlInt(789))
    assert len(list_a) == 4
    deser = to_json_and_back(list_a)
    print(deser)
    assert deser[0] == TlInt(1)
    assert deser[3] == TlInt(789)


def test_quote():
    obj = TlQuote(TlList([TlInt(1), TlString("foo")]))
    deser = to_json_and_back(obj)
    assert deser == obj


def test_future():
    obj = TlFuturePtr(2)
    deser = to_json_and_back(obj)
    assert deser == obj


CONVERSION_TEST_OBJS = [
    # --
    1,
    "foo",
    ["nested", ["big"], "list"],
    True,
    False,
    None,
]


@pytest.mark.parametrize("obj", CONVERSION_TEST_OBJS)
def test_conversion(obj):
    hark_obj = to_hark_type(obj)
    back = to_py_type(hark_obj)
    assert obj == back
