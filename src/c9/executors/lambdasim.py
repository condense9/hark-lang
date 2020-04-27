import multiprocessing
import time
import traceback
import warnings

import c9.controllers.ddb_model as db
import c9.controllers.ddb as ddb_controller

from ..machine import C9Machine
from ..machine.probe import Probe


class Invoker:
    def __init__(self, data_controller, evaluator_cls):
        self.data_controller = data_controller
        self.evaluator_cls = evaluator_cls

    def invoke(self, vmid, run_async=True):
        event = dict(
            # --
            session_id=self.data_controller.session.session_id,
            vmid=vmid,
        )
        p = multiprocessing.Process(target=resume_handler, args=(event,))
        p.start()


def resume_handler(event):
    session_id = event["session_id"]
    vmid = event["vmid"]
    session = db.Session.get(session_id)
    controller = ddb_controller.DataController(session)
    evaluator = ddb_controller.Evaluator
    invoker = Invoker(controller, evaluator)
    machine = C9Machine(vmid, invoker)
    machine.run()
    # TODO return something


def wait_for_finish(interface, sleep_interval=0.01, timeout=5):
    data_controller = interface.data_controller

    start_time = time.time()
    while not data_controller.finished:
        time.sleep(sleep_interval)
        if time.time() - start_time > timeout:
            raise RuntimeError("Timeout!")
