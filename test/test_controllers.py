"""Test Controller features"""
import pytest
import hark_lang.controllers.ddb_model as db
import hark_lang.machine.types as mt
from hark_lang.controllers.ddb import DataController as DdbController
from hark_lang.controllers.local import DataController as LocalController
from hark_lang.machine.arec import ActivationRecord
from hark_lang.machine.future import Future
from hark_lang.machine.probe import Probe
from hark_lang.machine.state import State

pytestmark = pytest.mark.ddblocal


def setup_module(module):
    if db.SessionItem.exists():
        db.SessionItem.delete_table()
    db.SessionItem.create_table(
        read_capacity_units=1, write_capacity_units=1, wait=True
    )


def NewDdbSession():
    base = db.init_base_session()
    return DdbController(db.new_session(), base)


CONTROLLERS = [
    LocalController,
    pytest.param(NewDdbSession, marks=[pytest.mark.ddblocal]),
]


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_new_thread(Controller):
    ctrl = Controller()
    t = ctrl.new_thread()
    assert t is not None
    assert ctrl.is_top_level(t)


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_result(Controller):
    ctrl = Controller()
    assert ctrl.result is None
    ctrl.result = "foo"
    assert ctrl.result == "foo"


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_arec(Controller):
    ctrl = Controller()
    r = ctrl.new_arec()
    assert r is not None

    rec = ActivationRecord(
        function=mt.TlFunctionPtr("foo", None),
        dynamic_chain=0,
        vmid=0,
        ref_count=0,
        call_site=0,
        bindings={"foo": mt.TlString("hello")},
    )
    ctrl.set_arec(r, rec)
    rec2 = ctrl.get_arec(r)
    assert rec == rec2

    previous = rec2.ref_count
    ctrl.increment_ref(r)
    rec2 = ctrl.get_arec(r)
    assert rec2.ref_count == previous + 1

    ctrl.decrement_ref(r)
    rec2 = ctrl.get_arec(r)
    assert rec2.ref_count == previous


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_state(Controller):
    ctrl = Controller()
    t = ctrl.new_thread()
    state = State([mt.TlString("foo"), mt.TlInt(2)])
    ctrl.set_state(t, state)

    state2 = ctrl.get_state(t)
    assert state == state2

    state.ip = 5
    ctrl.set_state(t, state)
    assert state == ctrl.get_state(t)


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_probe(Controller):
    ctrl = Controller()
    t = ctrl.new_thread()
    probe = Probe(0)
    probe.log("foobar")

    ctrl.set_probe_data(t, probe)
    logs = ctrl.get_probe_logs()
    assert len(logs) == 1
    assert logs[0].text == "foobar"


@pytest.mark.parametrize("Controller", CONTROLLERS)
def test_future(Controller):
    ctrl = Controller()
    t = ctrl.new_thread()
    f = Future()

    ctrl.set_future(t, f)
    f2 = ctrl.get_future(t)
    assert f.resolved == f2.resolved

    f.resolved = True
    ctrl.set_future(t, f)
    f2 = ctrl.get_future(t)
    assert f.resolved == f2.resolved

    assert f2.continuations == []
    ctrl.add_continuation(t, 5)
    f2 = ctrl.get_future(t)
    assert f2.continuations == [5]
