"""Runtime: DynamoDB for state, Lambda for execution"""

from ..executors.awslambda import LambdaExecutor
from ..controllers import ddb
from ..machine import c9e


def run(lambda_name, path_to_exe, *args, **kwargs) -> LambdaExecutor:
    executable = c9e.load(path_to_exe)
    executor = LambdaExecutor(lambda_name)
    return ddb.run(executor, executable, *args, **kwargs)
