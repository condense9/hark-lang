from .instruction import Instruction as I
from . import types as mt

# TODO: define __all__

##± Control Flow ±##############################################################


class Jump(I):
    """Move execution to a different point, relative to the current point"""

    op_types = [int]


class JumpIE(I):
    """Relative jump, only if top two elements on the stack are equal"""

    op_types = [int]


# TODO class JumpLong ?


class Future(I):
    """Take the top value from the stack and wrap it in a future.

    This essentially says - something is going to happen externally that the
    machine doesn't know about. The user is responsible for resolving this
    manually via the machine controller.

    For example, an external API call.

    """

    num_ops = 1


# This is a bit complex. Instead of a "user_future_id", just provide
# - A MakeFuture instruction, which returns the Future object
# - A FutureID instruction, which gets the future_id
# - You can then return the future object
# - And then you're responsible for resolving it
# - Since you can access the future_id, you know what you need to do.


class Wait(I):
    """Require the Nth item on the stack to be resolved before continuing.

    Will terminate the machine immediately if the item is an unresolved future,
    and (at the same time), add a continuation to that future.

    """

    op_types = [int]


class MFCall(I):
    """Call a *foreign* function"""

    op_types = [callable, int]

    def __eq__(self, other):
        # https://stackoverflow.com/questions/36852912/is-it-possible-to-know-if-two-python-functions-are-functionally-equivalent
        # Can't always check equality of functions! Best effort:
        return (
            type(self) == type(other)
            and self.operands[0].__name__ == other.operands[0].__name__
            and self.operands[1] == other.operands[1]
        )


class Return(I):
    """Return to the call site of the current frame"""


class Call(I):
    """Call a function (sync)

    This is the *application* of a function - first arg on the stack must
    *evaluate to* a Func name, which is the *reference to* a function.

    """

    op_types = [int]


class ACall(I):
    """Call a function (async)"""

    op_types = [int]


##± Conditions ±################################################################

# Like Exceptions, but a bit more powerful


class Signal(I):
    """Signal a condition"""

    op_types = [str]


class HandleCondition(I):
    """Register a condition handler

    Operands:
      - [0] str: Name of the condition to handle
      - [1] str: The handler function name

    Semantics:
    - A condition handler (or multiple) is attached to a given *function*
    - When the function returns, the condition handler is removed
    - If Signal is called with this condition name, this handler is called
    - A handler is another function that is called with the condition object
    - The handler gets all of the inputs to function, and can Restart, or Return
    - i.e., The handler gets the context of the original function
    - Restart means run the function again, with new (or same) inputs
    - Return means just immediately return a different value

    """

    op_types = [str, str]


class Restart(I):
    """Jump back to the original function"""


##± Data Access ±###############################################################


class PushV(I):
    """Push an immediate (literal) value onto the stack

    Useful, for example, for function-local constants.
    """

    op_types = [mt.TlType]


class Bind(I):
    """Take the top value off the stack and bind it to a register

    Maybe - if the given binding doesn't exist in the current binding stack,
    each parent stack will be searched until a matching binding is found. That'd
    make this machine far more dynamic! And make compilation harder.

    """

    op_types = [mt.TlSymbol]


class PushB(I):
    """Push a bound value onto the stack"""

    op_types = [mt.TlSymbol]


class Pop(I):
    """Remove top value from the stack and discard it"""


##± Data Manipulation ±#########################################################


class Eq(I):
    """Check whether the top two items on the stack are equal"""


class Atomp(I):
    """Check whether something is an atom"""


class List(I):
    """Make a list"""

    num_ops = 1


# Like cons, but not quite
class Conc(I):
    """Concatenate the top two elements on the stack"""


class First(I):
    """CAR (first element) of a list"""


class Rest(I):
    """CDR (all elements after first) of a list"""


class Nth(I):
    """Nth element of a list"""


class Nullp(I):
    """Check whether the top item on the stack is Null"""


##± Arithmetic ±################################################################


class Plus(I):
    """Add the top two elements on the stack"""


class Multiply(I):
    """Multiple the top two elements on the stack"""


##± Input-Output ±##############################################################

# (these are implementation-defined)


class Print(I):
    """Print the top value on the stack as a string"""


##± Misc ±######################################################################


class Sleep(I):
    """Sleep for some time"""
