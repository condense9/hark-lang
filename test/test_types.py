import pytest
import json

from c9.machine.types import *


def to_json_and_back(obj: C9Type):
    """Serialise an object to JSON and back"""
    ser = obj.serialise()
    jser = json.dumps(ser)
    jdeser = json.loads(jser)
    deser = C9Type.deserialise(jdeser)
    return deser


def test_true():
    original = C9True()
    ser = original.serialise()
    deser = C9Type.deserialise(ser)
    assert original == deser


def test_literals():
    int_a = C9Int(5)
    int_b = C9Int(3)
    int_c = C9Int(4)
    assert isinstance(int_a, int)
    assert int_a + int_b == 8
    ser = int_a.serialise()
    deser = C9Type.deserialise(ser)
    assert deser + int_c == 9


def test_list():
    list_a = C9List([C9Int(1), C9Int(2), C9Int(3)])
    assert len(list_a) == 3
    list_a.append(C9Int(789))
    assert len(list_a) == 4
    deser = to_json_and_back(list_a)
    print(deser)
    assert deser[0] == C9Int(1)
    assert deser[3] == C9Int(789)


def test_quote():
    obj = C9Quote(C9List([C9Int(1), C9String("foo")]))
    deser = to_json_and_back(obj)
    assert deser == obj


def test_future():
    obj = C9Future("foo")
    obj.resolved = True
    obj.value = C9List([C9Int(1), C9Int(2)])
    deser = to_json_and_back(obj)
    assert deser == obj


TYPE_TESTS = [1, "foo", ["nested", ["big"], "list"]]


@pytest.mark.parametrize("obj", TYPE_TESTS)
def test_conversion(obj):
    c9_obj = to_c9_type(obj)
    back = to_py_type(c9_obj)
    assert obj == back
