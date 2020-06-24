"""Run Teal with a dynamodb storage backend"""
from functools import partial

from ..controllers import ddb as ddb_controller
from ..executors import multiprocess as mp
from ..executors import thread as teal_thread
from .common import run_and_wait, wait_for_finish


def run_ddb_local(filename, function, args):
    """Run with dynamodb and python threading"""
    controller = ddb_controller.DataController.with_new_session()
    invoker = teal_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    return run_and_wait(controller, invoker, waiter, filename, function, args)


def run_ddb_processes(filename, function, args):
    """Run with dynamodb and python multiprocessing"""
    controller = ddb_controller.DataController.with_new_session()
    invoker = mp.Invoker(controller)
    waiter = partial(wait_for_finish, 1, 10)
    return run_and_wait(controller, invoker, waiter, filename, function, args)
