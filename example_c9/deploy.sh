#!/usr/bin/env bash

set -e
set -x

STAGE=${STAGE:-dev}
TOPFILE="hello.c9"

cp -r src aws
cp -r $TOPFILE aws

pushd aws

# https://serverless.com/framework/docs/providers/aws/cli-reference/deploy/
serverless deploy -s "${STAGE}"

# serverless invoke -f set_exe
# aws lambda invoke \
#     --function-name test-dev-set_exe \
#     --payload '{"content": "(def main () \"hello :)\""}' \
#     response.json

top=$(<$TOPFILE)

serverless invoke -f set_exe -d "{\"content\": \"$top\"}"

popd
