#!/usr/bin/env bash

set -e
set -x

STAGE=${STAGE:-dev}

cp -r src aws
cp -r ../src/c9 aws
cp serverless.tpl.yml aws/serverless.yml

pushd aws

# https://serverless.com/framework/docs/providers/aws/cli-reference/deploy/
serverless deploy -s "${STAGE}"

popd
