"""Create a lambda from the given zip file"""

import os.path
import sys

import c9.lambda_utils as utils

name = "runtest"

client = utils.get_lambda_client()
try:
    client.delete_function(FunctionName=name)
except client.exceptions.ResourceNotFoundException:
    pass

# Increase the timeout a bit - some of our tests have long-ish sleeps to
# simulate long-running tasks
utils.lambda_from_zip(
    name, "build/lambda.zip", handler="main.c9_handler", timeout=15,
)
print("OK")

# To check it exists:
#
# env AWS_DEFAULT_REGION="eu-west-2" awslocal lambda list-functions
