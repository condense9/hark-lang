from c9c.runtime.aws_db import *


def setup_module(module):
    if Session.exists():
        Session.delete_table()
    Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


def test_table_exists():
    assert Session.exists()


def test_new_session():
    s = new_session()
    sid = s.session_id
    assert len(s.futures) == 0
    assert len(list(Session.query(sid))) == 0
    s.save()
    assert len(list(Session.query(sid))) == 1


def test_new_machine():
    s = new_session()
    sid = s.session_id
    count = s.num_machines
    assert count == 0
    m = new_machine(s, [], is_top_level=True)
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
