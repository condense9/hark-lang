#!/bin/bash
#
# Tests the basic getting-started steps
# https://github.com/condense9/hark-lang#up-and-running-in-2-minutes

set -x
set -e

# Kill and fail test after this timeout:
TIMEOUT=120


main() {
    printf ":: Testing Hark v%s\n" "$(hark --version)"

    mkdir foo && cd foo
    hark init

    cat > service.hk <<EOF
fn main() {
  print("hi!");
}
EOF

    hark -q service.hk | tee output.txt

    grep -q "hi!" output.txt

    test "$(wc -l < output.txt)" -eq 2

    # Use a random UUID to avoid the CLI's question UI
    UUID="c3178518-7a04-4969-bd98-38acbc7f9229"

    hark -v deploy --uuid "${UUID}"

    hark -v invoke --uuid "${UUID}"

    hark -v stdout --uuid "${UUID}"

    hark -v events --uuid "${UUID}"

    hark -v destroy --uuid "${UUID}"
}


if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ( cmdpid=$BASHPID; (sleep "${TIMEOUT}"; kill -9 $cmdpid; exit 1) & main )
fi
