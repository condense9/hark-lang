from datetime import datetime
import uuid

from c9c.runtime.aws_db import *
from c9c.state import State


def setup_module(module):
    if Session.exists():
        Session.delete_table()
    Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)


def test_table_exists():
    assert Session.exists()


def test_create_session():
    sid = str(uuid.uuid4())
    s = Session(sid, created_at=datetime.now(), updated_at=datetime.now(),)
    s.save()
    assert len(list(Session.query(sid))) == 1


def test_add_machine():
    sid = str(uuid.uuid4())
    s = Session(sid, created_at=datetime.now(), updated_at=datetime.now(),)
    count = s.num_machines
    state = State()
    s.machines.append(MachineMap(machine_id=count, state=state))
    s.num_machines += 1
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.num_machines == count + 1
    assert retrieved.machines[0].machine_id == count
    assert retrieved.machines[0].state == state


def test_add_future():
    sid = str(uuid.uuid4())
    s = Session(sid, created_at=datetime.now(), updated_at=datetime.now(),)
    value = {"some": ["complex", {"thing": 1}]}
    s.futures.append(FutureMap(future_id=0, resolved=True, value=value))
    s.save()
    retrieved = Session.get(sid)
    assert retrieved.futures[0].future_id == 0
    assert retrieved.futures[0].resolved == True
    assert retrieved.futures[0].value == value
