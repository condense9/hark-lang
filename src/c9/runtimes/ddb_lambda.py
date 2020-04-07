"""Runtime: DynamoDB for state, Lambda for execution"""

from ..executors.awslambda import LambdaExecutor
from ..controllers import ddb
from ..machine import c9e


def run(lambda_name, executable, *args, **kwargs) -> LambdaExecutor:
    executor = LambdaExecutor(lambda_name)
    return ddb.run(executor, executable, *args, start_async=True, **kwargs)
