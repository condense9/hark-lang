"""Test that the machine executes instructions correctly"""

import pytest

from teal.machine import *

pytestmark = pytest.mark.skip(
    "Machine API changing rapidly -- use test_end2end.py for now."
)


def make_printer(buf: Buf) -> list:
    """Subroutine that prints to buf"""
    return [
        # --
        Wait(),
        Bind(0),
        PushB(0),
        FCall(buf.puts, 1),
        Wait(),
        Pop(),
        PushB(0),
        Return(),
        # --
    ]


################################################################################
## Tests


def concurrency_test():
    buf = Buf()
    functions = {
        "p": make_printer(buf),
        "times2": [
            # --
            Wait(),
            FCall(times2, 1),
            Return()
            # --
        ],
        "F_main": [
            # --
            Bind(0),
            PushB(0),
            Call("times2"),
            PushB(0),
            FCall(times3, 1),
            Wait(),
            Bind(0),
            Wait(),
            PushB(0),
            FCall(sum_two, 2),
            Call("p"),
            # --
        ],
    }
    data = LocalState(3)
    run_dbg_local(functions, data)
    print("===")
    print(buf.output)


def cond_test():
    buf = Buf()
    functions = {
        "p": make_printer(buf),
        "F_main": [
            # --
            PushV(True),
            JumpIE(2),  # len_subexpr_notequal is 2 (includes the jump)
            PushV("It's false!"),
            Jump(1),  # len_subexpr_equal is 1
            PushV("It's true!"),
            FCall(buf.puts, 1),
            Wait(),
            # --
        ],
    }
    # Try changing the value on the stack:
    data = LocalState(True)
    run_dbg_local(functions, data)
    print("===")
    print(buf.output)


if __name__ == "__main__":
    # concurrency_test()
    cond_test()
