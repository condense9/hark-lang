#!/usr/bin/env bash
#
# Create a lambda deployment package for Tl

set -e

# Get dir containing this script. It will work as long as the last component of
# the path used to find the script is not a symlink (directory links are OK).
# https://stackoverflow.com/questions/59895/get-the-source-directory-of-a-bash-script-from-within-the-script-itself
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


## Path to the resulting ZIP file, ready for use by aws.py
DEST=$(realpath "${1:-${DIR}/../src/hark_lang/dist_data/hark_lambda.zip}")

WORKDIR=${2:-${DIR}/../.hark_data}


###

WORKDIR="${WORKDIR}/hark_build"
mkdir -p "${WORKDIR}"

poetry export -f requirements.txt > "${WORKDIR}/requirements.txt"

pushd "${WORKDIR}" >/dev/null

mkdir -p libs

# SKIP_DEPS=yes to skip installing dependencies if you know they haven't changed
[[ -z "${SKIP_DEPS}" ]] && \
    pip install -q --target libs -r requirements.txt >/dev/null
rm -rf libs/boto*

# Install Hark manually
cp -r "${DIR}/../src/hark_lang" libs
rm -rf libs/hark_lang/dist_data

cd libs && zip -u -q -r "${DEST}" . -x "*__pycache__*"

popd >/dev/null

printf "Built Hark Lambda zip: %s\n" "${DEST}"
