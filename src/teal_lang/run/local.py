"""Run Teal with in-memory storage"""
import os
from functools import partial

from ..controllers import local as local
from ..executors import thread as teal_thread
from ..machine.types import to_py_type
from .common import LOG, run_and_wait, wait_for_finish


def run_local(filename, function, args, timeout_s=10):
    LOG.debug(f"PYTHONPATH: {os.getenv('PYTHONPATH')}")
    controller = local.DataController()
    invoker = teal_thread.Invoker(controller)
    check_period = 0.1
    waiter = partial(wait_for_finish, check_period, timeout_s)
    return run_and_wait(controller, invoker, waiter, filename, function, args)
