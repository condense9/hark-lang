"""Runtime: DynamoDB for state, Lambda for execution"""

from .executors import awslambda
from .controllers import ddb


def run_lambda(*args, **kwargs):
    executor = awslambda.LambdaRunner()
    return run(executor, *args, **kwargs)
