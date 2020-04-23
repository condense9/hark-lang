from .controllers import ddb
from .controllers.local import LocalController, run_exe
from .executors import thread
from .executors import awslambda
from .machine import c9e
from .machine.executable import Executable


class Runtime:
    """A C9 runtime configuration"""

    def run(self, executable: Executable, args):
        """Call the given EXECUTABLE, passing ARGS to F_main"""
        raise NotImplementedError


class DdbLambda(Runtime):
    """Runtime: DynamoDB for state, Lambda for execution"""

    def __init__(lambda_name, *, timeout=10, start_async=False, **kwargs):
        self.lambda_name = lambda_name
        self.timeout = timeout
        self.start_async = start_async
        self.executor = awslambda.LambdaExecutor(self.lambda_name)
        super().__init__(self, **kwargs)

    def run_new(self, executable, args):
        return ddb.run(
            self.executor,
            executable,
            args,
            do_probe=self.do_probe,
            timeout=self.timeout,
            sleep_interval=self.sleep_interval,
            start_async=self.start_async,
        )

    def run_existing(self, executable, session_id, machine_id):
        return ddb.run_existing(
            self.executor, executable, session_id, machine_id, do_probe=self.do_probe
        )


class DdbThreaded(Runtime):
    """Runtime: DynamoDB for state, Python threading for execution"""

    def run(executable, args):
        executor = thread.ThreadExecutor(ddb.run_existing)
        return ddb.run(executor, executable, args)


class Threaded(Runtime):
    """Local in-memory storage and Python threads"""

    def __init__(self, sleep_interval=0.01, **kwargs):
        self.sleep_interval = sleep_interval
        super().__init__(**kwargs)

    def run(executable, args) -> LocalController:
        # TODO use threaded executor - same interface as ddb
        return run_exe(
            executable, args, do_probe=self.do_probe, sleep_interval=self.sleep_interval
        )
