#!/usr/bin/env bash

# docker pull amazon/dynamodb-local

set -x
set -e


PORT=9000
TABLE=TlSessions


CID=$(docker run --rm -d -p ${PORT}:8000 amazon/dynamodb-local)

quit() {
    echo Stopping DynamoDB local Docker container
    docker kill "${CID}"
}
trap 'quit' SIGINT


export AWS_DEFAULT_REGION=eu-west-2

aws dynamodb create-table --table-name ${TABLE} \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:${PORT} >/dev/null

set +x
echo
echo Export the following variables for Teal:
echo
echo DYNAMODB_TABLE=${TABLE}
echo DYNAMODB_ENDPOINT=http://localhost:${PORT}
echo TL_REGION=${AWS_DEFAULT_REGION}
echo

DYNAMO_ENDPOINT=http://localhost:${PORT} dynamodb-admin
