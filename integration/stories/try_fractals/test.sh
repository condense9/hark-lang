#!/bin/bash
#
# Tests the fractals example
# https://github.com/condense9/teal-lang/tree/master/examples/fractals

set -x
set -e

# Kill and fail test after this timeout:
TIMEOUT=120


main() {
    printf ":: Testing Teal v%s\n" "$(teal --version)"

    echo FRACTALS_BUCKET="${FRACTALS_BUCKET}" > teal_env.txt

    sed -i "s/teal-example-data/${FRACTALS_BUCKET}/" teal.toml

    UUID="c3178518-7a04-4969-bd98-38acbc7f9229"

    teal -v deploy --uuid "${UUID}"

    teal -v invoke --uuid "${UUID}"

    teal -v destroy --uuid "${UUID}"
}


if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ( cmdpid=$BASHPID; (sleep "${TIMEOUT}"; kill -9 $cmdpid; exit 1) & main )
fi
