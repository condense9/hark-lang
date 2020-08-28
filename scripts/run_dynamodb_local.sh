#!/usr/bin/env bash

# npm install -g dynamodb-admin
# docker pull amazon/dynamodb-local

set -x
set -e


PORT=9000
TABLE=HarkSessions

AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-eu-west-2}
export AWS_DEFAULT_REGION

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
        AttributeName=item_id,AttributeType=S \
        --key-schema AttributeName=session_id,KeyType=HASH \
        AttributeName=item_id,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url http://localhost:${PORT}
fi

set +x
echo
echo Set these environment variables for Hark:
echo
echo "export DYNAMODB_ENDPOINT=http://localhost:${PORT}"
echo
echo "export DYNAMODB_TABLE=${TABLE}"
echo
echo "And make sure your region is correct! ${AWS_DEFAULT_REGION}"
echo
echo "Also make sure AWS_PROFILE is not set!"
echo

DYNAMO_ENDPOINT=http://localhost:${PORT} dynamodb-admin
