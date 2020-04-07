#!/usr/bin/env bash
#
# Docker compose didn't want to pick up the API key, so here we are.

. .localstack_api_key
SERVICES=serverless,logs \
        DEFAULT_REGION=eu-west-2 \
        DEBUG=1 \
        localstack start
