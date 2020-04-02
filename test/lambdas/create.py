import os.path
import sys

import c9c.lambda_utils as utils

zipfile = sys.argv[1]
assert zipfile.endswith(".zip")
name = os.path.splitext(os.path.basename(zipfile))[0]

client = utils.get_lambda_client()
try:
    client.delete_function(FunctionName=name)
except client.exceptions.ResourceNotFoundException:
    pass

# Increase the timeout a bit - some of our tests have long-ish sleeps to
# simulate long-running tasks
utils.lambda_from_zip(name, zipfile, timeout=15)
print("OK")

# To check it exists:
#
# env AWS_DEFAULT_REGION="eu-west-2" awslocal lambda list-functions
