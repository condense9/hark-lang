"""Run Teal with in-memory storage"""
import os
from functools import partial

from ..controllers import local as local
from ..executors import thread as teal_thread
from ..machine.types import to_py_type
from .common import LOG, run_and_wait, wait_for_finish


def run_local(filename, function, args):
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.DataController()
    invoker = teal_thread.Invoker(controller)
    waiter = partial(wait_for_finish, 0.1, 10)
    run_and_wait(controller, invoker, waiter, filename, function, args)
    return controller.result
