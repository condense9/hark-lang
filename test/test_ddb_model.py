"""Test the AWS (pynamodb) interface"""
import pytest

from teal_lang.controllers.ddb_model import *

pytestmark = pytest.mark.ddblocal


def setup_module(module):
    if Session.exists():
        Session.delete_table()
    Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


def test_table_exists():
    assert Session.exists()


def test_new_session():
    assert len(list(Session.scan())) == 0
    with pytest.raises(Session.DoesNotExist):
        s = new_session()

    init_base_session()
    assert len(list(Session.scan())) == 1

    s = new_session()
    sid = s.session_id
    s.save()
    assert len(list(Session.scan())) == 2
    assert len(s.machines) == 0


def test_new_machine():
    s = new_session()
    sid = s.session_id
    count = s.num_machines
    assert count == 0
    m = new_machine(s, [])
    assert isinstance(m, int)
    state = s.machines[m].state
    s.save()

    retrieved = Session.get(sid)
    assert retrieved.num_machines == count + 1
    assert retrieved.machines[0].state == state


def test_lock_saves():
    """Test that lock refreshes on entry and saves on exit"""
    s1 = new_session()
    lock = SessionLocker(s1)
    # Modify an arbitrary item to check refresh()
    s1.num_machines = 5
    with lock:
        s1.finished = True
    # Load in another session to check save()
    s2 = Session.get(s1.session_id)
    assert s2.num_machines == 0
    assert s2.finished == True


def test_lock_reusable():
    """A single session lock should be reusable"""
    s1 = new_session()
    lock = SessionLocker(s1)
    with lock:
        s1.num_futures = 1
    with lock:
        s1.num_futures = 2
    assert s1.num_futures == 2


def test_lock_reentrant():
    """Test that a lock cannot be acquired more than once at a time"""
    s1 = new_session()
    lock = SessionLocker(s1, timeout=0.01)
    lock2 = SessionLocker(s1, timeout=0.01)
    assert not s1.locked
    with lock:
        s1.finished = True
        assert s1.locked
        with pytest.raises(LockTimeout):
            with lock:
                pass
