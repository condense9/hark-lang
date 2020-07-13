"""Run Teal with a dynamodb storage backend"""
from functools import partial

from ..machine.controller import ControllerError
from ..controllers import ddb as ddb_controller
from ..executors import multiprocess as mp
from ..executors import thread as teal_thread
from .common import run_and_wait, wait_for_finish

import pynamodb


def run_ddb_local(filename, function, args, timeout=10):
    """Run with dynamodb and python threading"""
    controller = ddb_controller.DataController.with_new_session()
    invoker = teal_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 1, timeout)
    try:
        return run_and_wait(controller, invoker, waiter, filename, function, args)
    except pynamodb.exceptions.PynamoDBException as exc:
        raise ControllerError("Database error: {exc}") from exc


def run_ddb_processes(filename, function, args, timeout=10):
    """Run with dynamodb and python multiprocessing"""
    controller = ddb_controller.DataController.with_new_session()
    invoker = mp.Invoker(controller)
    waiter = partial(wait_for_finish, 1, timeout)
    try:
        return run_and_wait(controller, invoker, waiter, filename, function, args)
    except pynamodb.exceptions.PynamoDBException as exc:
        raise ControllerError("Database error: {exc}") from exc
