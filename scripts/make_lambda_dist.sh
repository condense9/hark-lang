#!/usr/bin/env bash
#
# Create a lambda deployment package for Tl

set -e

# Get dir containing this script. It will work as long as the last component of
# the path used to find the script is not a symlink (directory links are OK).
# https://stackoverflow.com/questions/59895/get-the-source-directory-of-a-bash-script-from-within-the-script-itself
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


## Path to the resulting ZIP file
DEST=${1:-${DIR}/../teal_lambda.zip}

WORKDIR=${2:-${DIR}/../.teal_data}


###

WORKDIR="${WORKDIR}/teal_build"
mkdir -p "${WORKDIR}"

FILENAME=$(basename "${DEST}")

poetry export -f requirements.txt > "${WORKDIR}/requirements.txt"

pushd "${WORKDIR}" >/dev/null

mkdir -p libs

# SKIP_DEPS=yes to skip installing dependencies if you know they haven't changed
[[ -z "${SKIP_DEPS}" ]] && \
    pip install -q --target libs -r requirements.txt 2>/dev/null
rm -rf libs/boto*

# Install Teal manually
cp -r "${DIR}/../src/teal_lang" libs

cd libs && zip -u -q -r "../${FILENAME}" . -x "*__pycache__*"

popd >/dev/null

cp "${WORKDIR}/${FILENAME}" "${DEST}"

printf "Success: %s\n" "${FILENAME}"
