import os.path
import sys

import utils.lambda_utils as utils

zipfile = sys.argv[1]
assert zipfile.endswith(".zip")
name = os.path.splitext(os.path.basename(zipfile))[0]

utils.lambda_from_zip(name, zipfile)
print("OK")
