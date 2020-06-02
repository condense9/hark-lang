#!/usr/bin/env bash
#
# Create a lambda layer ZIP package

set -e

## Source code directory
SRC=${1:-src}

## Path to the resulting ZIP file
DEST=${2:-srclayer.zip}


FILENAME=$(basename "${DEST}")

TMP=$(mktemp -d)

mkdir -p "${TMP}/python"
cp -r "${SRC}" "${TMP}/python/"

pip install -q --target "${TMP}/python" -r requirements.txt

pushd "${TMP}" >/dev/null
zip -q -r "${FILENAME}" python -x "*__pycache__*"
popd >/dev/null

cp "${TMP}/${FILENAME}" "${DEST}"
rm -rf "${TMP}"

printf "\nSuccess: %s\n" "${FILENAME}"
