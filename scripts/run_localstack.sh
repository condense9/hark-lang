#!/usr/bin/env bash
#
# https://github.com/localstack/localstack
#

# Get dir containing this script. It will work as long as the last component of
# the path used to find the script is not a symlink (directory links are OK).
# https://stackoverflow.com/questions/59895/get-the-source-directory-of-a-bash-script-from-within-the-script-itself
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


TMPDIR=/private$TMPDIR docker-compose -f "${DIR}/docker-compose.yml" up
