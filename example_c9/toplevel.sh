#!/usr/bin/env bash

top=$(<hello.c9)

python -c 'import json; print(json.dumps({"content": open("hello.c9").read()}))' \
       > aws/toplevel.json

pushd aws
serverless invoke -f set_exe -p toplevel.json
popd
