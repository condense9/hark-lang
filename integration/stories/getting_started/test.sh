#!/bin/bash
#
# Tests the basic getting-started steps
# https://github.com/condense9/teal-lang#up-and-running-in-2-minutes

set -x
set -e

# Kill and fail test after this timeout:
TIMEOUT=120


main() {
    printf ":: Testing Teal v%s\n" "$(teal --version)"

    mkdir foo && cd foo
    teal init

    cat > service.tl <<EOF
fn main() {
  print("hi!");
}
EOF

    teal -q service.tl | tee output.txt

    grep -q "hi!" output.txt

    test "$(wc -l < output.txt)" -eq 2

    # Use a random UUID to avoid the CLI's question UI
    UUID="c3178518-7a04-4969-bd98-38acbc7f9229"

    teal -v deploy --uuid "${UUID}"

    teal -v invoke --uuid "${UUID}"

    teal -v stdout --uuid "${UUID}"

    teal -v events --uuid "${UUID}"

    teal -v destroy --uuid "${UUID}"
}


if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    ( cmdpid=$BASHPID; (sleep "${TIMEOUT}"; kill -9 $cmdpid; exit 1) & main )
fi
