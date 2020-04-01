"""Runtime: DynamoDB for state, Lambda for execution"""

from .executors import awslambda
from .controllers import ddb


def run(*args, **kwargs):
    executor = awslambda.LambdaRunner()
    return ddb.run(executor, *args, **kwargs)
