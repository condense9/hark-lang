#!/usr/bin/env bash

set -x
set -e

C9_VERSION=${C9_VERSION:-0.1.0}

poetry build
mkdir -p aws
pip install --upgrade --target aws "../dist/c9-${C9_VERSION}.tar.gz"
