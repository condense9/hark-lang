#!/usr/bin/env bash

# docker pull amazon/dynamodb-local

set -x
set -e


PORT=9000
TABLE=C9Sessions


docker run -p ${PORT}:8000 amazon/dynamodb-local &

quit() {
    kill $!
}
trap 'quit' SIGINT


aws dynamodb create-table --table-name ${TABLE} \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:${PORT} >/dev/null

DYNAMO_ENDPOINT=http://localhost:${PORT} dynamodb-admin
