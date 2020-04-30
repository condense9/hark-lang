#!/usr/bin/env bash

# docker pull amazon/dynamodb-local

set -x
set -e


PORT=9000
TABLE=TealSessions


CID=$(docker run --rm -d -p ${PORT}:8000 amazon/dynamodb-local)

quit() {
    echo Stopping DynamoDB local Docker container
    docker kill "${CID}"
}
trap 'quit' SIGINT


# optionally, create the table too
if [[ -n "$1" ]]; then
    aws dynamodb create-table --table-name ${TABLE} \
        --attribute-definitions AttributeName=session_id,AttributeType=S \
        --key-schema AttributeName=session_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url http://localhost:${PORT} >/dev/null
fi

set +x
echo
echo Set this environment variable for Teal:
echo
echo "export DYNAMODB_ENDPOINT=http://localhost:${PORT}"
echo
echo And, optionally:
echo
echo "export DYNAMODB_TABLE=${TABLE}"
echo "export TL_REGION=${AWS_DEFAULT_REGION}"
echo
echo

DYNAMO_ENDPOINT=http://localhost:${PORT} dynamodb-admin
