#!/usr/bin/env bash

pushd aws
sls invoke -f new
popd
