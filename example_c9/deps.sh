#!/usr/bin/env bash

set -x
set -e

C9_VERSION=${C9_VERSION:-0.1.0}

poetry build
pip install --upgrade --target libs "../dist/c9-${C9_VERSION}.tar.gz"
