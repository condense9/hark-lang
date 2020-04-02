"""Runtime: DynamoDB for state, Python threading for execution"""

from .executors import thread
from .controllers import ddb
from ..machine import c9e


def run(path_to_exe, *args, **kwargs):
    executable = c9e.load(path_to_exe)
    executor = thread.ThreadExecutor(ddb.run_existing)
    return ddb.run(executor, executable, *args, **kwargs)
