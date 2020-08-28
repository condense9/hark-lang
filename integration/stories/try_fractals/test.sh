#!/bin/bash
#
# Tests the fractals example
# https://github.com/condense9/hark-lang/tree/master/examples/fractals

set -x
set -e

# Kill and fail test after this timeout:
TIMEOUT=120


main() {
    printf ":: Testing Hark v%s\n" "$(hark --version)"

    echo FRACTALS_BUCKET="${FRACTALS_BUCKET}" > hark_env.txt

    sed -i "s/hark-example-data/${FRACTALS_BUCKET}/" hark.toml

    UUID="c3178518-7a04-4969-bd98-38acbc7f9229"

    hark -v deploy --uuid "${UUID}"

    hark -v invoke --uuid "${UUID}"

    hark -v destroy --uuid "${UUID}"
}


if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ( cmdpid=$BASHPID; (sleep "${TIMEOUT}"; kill -9 $cmdpid; exit 1) & main )
fi
