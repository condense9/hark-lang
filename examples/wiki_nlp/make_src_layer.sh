#!/usr/bin/env bash
#
# Create a lambda layer ZIP package

SRC_DIR=src
ZIP_NAME=srclayer.zip


##

set -e

TMP=$(mktemp -d)

mkdir -p "${TMP}/python"
cp -r "${SRC_DIR}" "${TMP}/python/"

pip install -q --target "${TMP}/python" -r requirements.txt

pushd "${TMP}"
zip -q -r "${ZIP_NAME}" python -x "*__pycache__*"
popd

cp "${TMP}/${ZIP_NAME}" .
rm -rf "${TMP}"

printf "\nSuccess: %s\n" "${ZIP_NAME}"
