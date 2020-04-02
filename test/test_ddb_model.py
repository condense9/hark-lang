"""Test the AWS (pynamodb) interface"""
import pytest

from c9.controllers.ddb_model import *


def setup_module(module):
    if Session.exists():
        Session.delete_table()
    Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


def test_table_exists():
    assert Session.exists()


def test_new_session():
    assert len(list(Session.scan())) == 0
    s = new_session()
    sid = s.session_id
    assert len(list(Session.scan())) == 1
    assert len(s.futures) == 0


def test_new_machine():
    s = new_session()
    sid = s.session_id
    count = s.num_machines
    assert count == 0
    m = new_machine(s, [], top_level=True)
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.num_machines == count + 1
    assert retrieved.machines[0].state == m.state


def test_add_future():
    s = new_session()
    count = s.num_machines
    sid = s.session_id
    f = new_future(s)
    val = {"some": ["complex", {"thing": 1}]}
    f.value = val
    f.resolved = True
    print(s.futures)
    assert s.futures[0] == f
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.futures[0].future_id == f.future_id
    assert retrieved.futures[0].resolved == True
    assert retrieved.futures[0].value == val


def test_object_persistence():
    """Demonstrate that nested objects change on refresh"""
    s1 = new_session()
    m = new_machine(s1, [])
    s1_future = s1.futures[0]
    s1.save()
    s2 = Session.get(s1.session_id)
    s2.futures[0].resolved = True
    s2.save()
    s1.refresh()
    s2_future = s2.futures[0]
    assert id(s2_future) != id(s1_future)
    assert s2_future.resolved == True
    assert s1_future.resolved == False


def test_lock_saves():
    """Test that lock refreshes on entry and saves on exit"""
    s1 = new_session()
    lock = SessionLocker(s1)
    # Modify an arbitrary item to check refresh()
    s1.num_futures = 5
    with lock:
        s1.finished = True
    # Load in another session to check save()
    s2 = Session.get(s1.session_id)
    assert s2.num_futures == 0
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
    """Test that a lock can be acquired more than once at a time"""
    s1 = new_session()
    lock = SessionLocker(s1, timeout=0.1)
    lock2 = SessionLocker(s1, timeout=0.1)
    assert not s1.locked
    with lock:
        s1.finished = True
        assert lock.lock_count == 1
        assert s1.locked
        # The *same* lock on a session can be acquired more than once
        with lock:
            assert lock.lock_count == 2
        # But a different lock on the same session cannot
        with pytest.raises(LockTimeout):
            with lock2:
                pass
