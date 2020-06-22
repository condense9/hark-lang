"""Test controller features"""
import pytest

import teal_lang.controllers.ddb_model as db
from teal_lang.controllers.ddb import DataController as DdbController
from teal_lang.controllers.local import DataController as LocalController

from teal_lang.machine.arec import ActivationRecord

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


@pytest.mark.parametrize("make_controller", CONTROLLERS)
def test_new_thread(make_controller):
    ctrl = make_controller()
    t = ctrl.new_thread()
    assert t is not None
    assert ctrl.is_top_level(t)


@pytest.mark.parametrize("make_controller", CONTROLLERS)
def test_result(make_controller):
    ctrl = make_controller()
    assert ctrl.result is None
    ctrl.result = "foo"
    assert ctrl.result == "foo"


@pytest.mark.parametrize("make_controller", CONTROLLERS)
def test_arec(make_controller):
    ctrl = make_controller()
    r = ctrl.new_arec()
    assert r is not None
    rec = ActivationRecord.sample()
    ctrl.set_arec(r, rec)
