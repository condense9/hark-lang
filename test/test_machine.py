"""Test that the machine executes instructions correctly"""

from machine import *
from simple_functions import *
from utils import run_dbg_local


def simple_test_scratch():
    # trivial flow: main(x) = print(f = 2x + 3x)
    functions = {
        "times2": [  #        heap stacks
            # --     # ........[ ] [ P ? ]
            Wait(),  # ........[ ] [ P x ]  FCall requires concrete argument
            FCall(times2),  # .[ ] [ P y ]
            Return()  # .......[ ] [ P=y ]
            # --
        ],
        # Main is special - the single argument is a concrete value. All other
        # functions assume nothing
        "F_main": [  #             heap  stacks
            # --                  []   [ P x ]
            Bind(0),  # ..........[x]  [ P x ]
            PushB(0),
            Call("times2"),  # ...[x]  [ P Y ]    [ Y x ]
            PushB(0),  # .........[x]  [ P Y x ]  [ Y x ]
            Call("times3"),  # ...[x]  [ P Y Z ]  [ Y x ]  [ Z x ]
            Wait(),  # ...........[x]  [ P Y z ]  [ Y x ]
            Wait(),  # ...........[x]  [ P y z ]
            FCall("sum_two"),  # .[x]  [ P F ]  [ F y z ]
            Wait(),  # ...........[x]  [ P f ]
            FCall(printit),  # ...[x]  [ P f ]
            # Not necessary, heap isn't shared:
            # Unbind(0),  # ........[]   [ P f ]
            Return(),
            # --
        ],
    }
    data = LocalState([3])
    machine = LocalMachine(functions, data, 0)
    run_dbg_local(machine, max_steps=20)


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
