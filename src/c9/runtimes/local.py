from ..machine import c9e
from ..controllers.local import LocalController, run_exe

# TODO use threaded executor - same interface as ddb


def run(path_to_exe: str, args: list, **kwargs) -> LocalController:
    """Load executable from file and run it"""
    executable = c9e.load(path_to_exe)
    return run_exe(executable, args, **kwargs)
