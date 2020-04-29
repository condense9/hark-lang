#!/usr/bin/env bash
#
# Upload the program file
set -euo pipefail

## The file to upload
PROGRAM=$1

TMP=$(mktemp)

python -c "import json; print(json.dumps({\"content\": open(\"${PROGRAM}\").read()}))" \
       > "${TMP}"

serverless invoke -f set_exe -p "${TMP}" | jq "."
