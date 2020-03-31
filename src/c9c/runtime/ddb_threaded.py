"""Runtime: DynamoDB for state, Python threading for execution"""

from .executors import thread
from .controllers import ddb


def run(*args, **kwargs):
    runner = thread.ThreadExecutor(ddb.run_existing)
    return ddb.run(runner, *args, **kwargs)
