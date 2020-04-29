#!/usr/bin/env bash
#
# Example test against the deployed function

set -e
set -x

## JSON configuration for the new function
ARGS=${1:-test_printer.json}


# Double jq to pretty print - maybe there's a nicer way...
sls invoke -f new -p "${ARGS}" | jq -r | jq .
