"""Shared Constants"""


# Name of the top-level (entrypoint) module in C9 lambdas
HANDLER_MODULE = "main"

# Name of the function to handle new events
FN_HANDLE_NEW = "handle_new"

# Name of the function to handle existing machines
FN_HANDLE_EXISTING = "handle_existing"

# Qualified name of the handler for new events
HANDLE_NEW = f"{HANDLER_MODULE}.{FN_HANDLE_NEW}"

# Qualified name of the handler for existing machines
HANDLE_EXISTING = f"{HANDLER_MODULE}.{FN_HANDLE_EXISTING}"

# Directory of lambda source code in the deployment directory
LAMBDA_DIRNAME = "lambda_code"

# Paths of things in the lambda directory
SRC_PATH = "src"
LIB_PATH = "lib"
EXE_PATH = "exe"

# Name of the file containing infrastructure outputs (in the lambda directory)
OUTPUTS_FILENAME = "outputs.json"
