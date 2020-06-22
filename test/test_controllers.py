"""Test Controller features"""
import pytest

import teal_lang.controllers.ddb_model as db
from teal_lang.controllers.ddb import DataController as DdbController
from teal_lang.controllers.local import DataController as LocalController

from teal_lang.machine.arec import ActivationRecord
from teal_lang.machine.future import Future
from teal_lang.machine.state import State
from teal_lang.machine.probe import Probe

pytestmark = pytest.mark.ddblocal


def setup_module(module):
    if db.Session.exists():
        db.Session.delete_table()
    db.Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
    db.init_base_session()


def NewDdbSession():
    return DdbController(db.new_session())


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

    rec = ActivationRecord.sample()
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
    state = State.sample()
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
    probe = Probe()
    probe.log("foobar")

    ctrl.set_probe(t, probe)
    p2 = ctrl.get_probe(t)
    assert probe.logs == p2.logs


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
