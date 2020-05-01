"""Run Teal with a dynamodb storage backend"""
from functools import partial

from ..controllers import ddb as ddb_controller
from ..controllers import ddb_model as db
from ..executors import multiprocess as mp
from ..executors import thread as teal_thread
from .common import LOG, run_and_wait, wait_for_finish


def run_ddb_local(filename, function, args):
    db.init_base_session()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = teal_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)
    return controller.result


def run_ddb_processes(filename, function, args):
    db.init_base_session()
    session = db.new_session()
    lock = db.SessionLocker(session)
    controller = ddb_controller.DataController(session, lock)
    invoker = mp.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)
    return controller.result
