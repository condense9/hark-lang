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

utils.lambda_from_zip(name, zipfile)
print("OK")
