#!/usr/bin/env bash
#
# Create a lambda layer ZIP package

set -e
set -x

## Source code directory
SRC=${1:-src}

## Name of the ZIP file
LAYER=${2:-srclayer.zip}


TMP=$(mktemp -d)

mkdir -p "${TMP}/python"
cp -r "${SRC}" "${TMP}/python/"

pushd "${TMP}"
zip -q -r "${LAYER}" python -x "*__pycache__*"
popd

cp "${TMP}/${LAYER}" .
rm -rf "${TMP}"
