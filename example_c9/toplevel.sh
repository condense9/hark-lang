#!/usr/bin/env bash

top=$(<hello.c9)

pushd aws
serverless invoke -f set_exe -d "{\"content\": \"$top\"}"
popd
