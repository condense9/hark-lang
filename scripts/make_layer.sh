#!/usr/bin/env bash
#
# Create a lambda layer ZIP package

set -e

## Source code directory
SRC=${1:-src}

## Path to the resulting ZIP file
DEST=${2:-srclayer.zip}

WORKDIR=${3:-.hark_data}

###

WORKDIR="${WORKDIR}/layer_build"
mkdir -p "${WORKDIR}"

FILENAME=$(basename "${DEST}")

mkdir -p "${WORKDIR}/python"
cp -r "${SRC}" "${WORKDIR}/python/"

pip install -q --target "${WORKDIR}/python" -r requirements.txt

pushd "${WORKDIR}" >/dev/null
zip -FS -q -r "${FILENAME}" python -x "*__pycache__*"
popd >/dev/null

cp "${WORKDIR}/${FILENAME}" "${DEST}"

printf "\nSuccess: %s\n" "${FILENAME}"
