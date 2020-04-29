#!/usr/bin/env bash

pushd aws || exit

# Double jq to pretty print - maybe there's a nicer way...
sls invoke -f new -p ../test_args.json | jq -r | jq .

popd
