from ..machine import c9e
from ..controllers.local import LocalController, run_exe

# TODO use threaded executor - same interface as ddb


def run(executable, args: list, **kwargs) -> LocalController:
    """Load executable from file and run it"""
    return run_exe(executable, args, **kwargs)
