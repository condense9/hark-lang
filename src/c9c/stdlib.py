"""Standard library of utilities"""

from .lang import *
from .machine import Wait


@Func
def wait_for(a):
    return Asm([a], [Wait(0)])


@Func
def Map(function, lst):
    """Map (sync) function (sync OR async) over all values in lst

    NOTE: Map is Sync, but if function is Async there will be Futures in the
    list! Use MapResolve to get a list of resolved values.

    """
    # function is a symbol referring to a function, so must Apply it
    return If(
        # --
        Nullp(lst),
        [],
        Cons(Funcall(function, First(lst)), Map(function, Rest(lst)),),
    )


@Func
def MapResolve(function, lst):
    """Map and then resolve all values"""
    return Map(wait_for, Map(function, lst))
