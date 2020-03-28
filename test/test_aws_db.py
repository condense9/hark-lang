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
    assert len(list(Session.query(sid))) == 0
    s.save()
    assert len(list(Session.query(sid))) == 1


def test_new_machine():
    s = new_session()
    sid = s.session_id
    count = s.num_machines
    m = new_machine(s)
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.num_machines == count + 1


def test_add_future():
    s = new_session()
    sid = s.session_id
    value = {"some": ["complex", {"thing": 1}]}
    s.futures.append(FutureMap(future_id=0, resolved=True, value=value))
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.futures[0].future_id == 0
    assert retrieved.futures[0].resolved == True
    assert retrieved.futures[0].value == value
