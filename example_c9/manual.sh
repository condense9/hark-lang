#!/usr/bin/env bash
#
# For when serverless framework doesn't work.
# https://github.com/localstack/serverless-localstack/issues/86

set -e
set -x

TABLE=C9Sessions

# https://github.com/localstack/localstack
EDGE="--endpoint-url http://localhost:4566"


aws ${EDGE} dynamodb list-tables | jq ".TableNames" | grep -q "${TABLE}"
GOT_TABLE=$?

if [ $GOT_TABLE ]; then
    echo "Deleting old table"
    aws dynamodb delete-table --table-name "${TABLE}"
    sleep 1
fi

aws dynamodb create-table --table-name "${TABLE}" \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    ${EDGE} >/dev/null


PKG=package.zip
cd dist && zip -r -g "../${PKG}" . -x "*__pycache__*"

# FIXME - WIP

aws lambda create-function --function-name setexe \
    --runtime python3.8 \
    --role lambda_basic_execution \
    --handler c9.src.c9.executors.awslambda.set_exe \
    --zip-file "fileb:://${PKG}"

aws lambda create-function --function-name resume \
    --runtime python3.8 \
    --role lambda_basic_execution \
    --handler c9.src.c9.executors.awslambda.resume \
    --zip-file "fileb:://${PKG}"

aws lambda create-function --function-name new \
    --runtime python3.8 \
    --role lambda_basic_execution \
    --handler c9.src.c9.executors.awslambda.new \
    --zip-file "fileb:://${PKG}"
