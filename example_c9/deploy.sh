#!/usr/bin/env bash

set -e
set -x

STAGE=${STAGE:-dev}

# https://serverless.com/framework/docs/providers/aws/cli-reference/deploy/
serverless deploy -s "${STAGE}"
