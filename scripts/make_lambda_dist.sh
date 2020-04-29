#!/usr/bin/env bash
#
# Create a lambda deployment package for Tl

set -e
set -x

## Name of the resulting ZIP file
DIST=${1:-dist.zip}


# Get dir containing this script. It will work as long as the last component of
# the path used to find the script is not a symlink (directory links are OK).
# https://stackoverflow.com/questions/59895/get-the-source-directory-of-a-bash-script-from-within-the-script-itself
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

TMP=$(mktemp -d)

poetry export -f requirements.txt > "${TMP}/requirements.txt"

pushd "${TMP}"

mkdir libs
pip install -q --target libs -r requirements.txt
rm -rf libs/boto*

# Install Teal manually
cp -r "${DIR}/../src/teal" libs

cd libs && zip -q -r "../${DIST}" . -x "*__pycache__*"

popd

cp "${TMP}/${DIST}" .
rm -rf "${TMP}"
