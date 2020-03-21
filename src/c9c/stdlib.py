"""Standard library of utilities"""

from lang import *
from machine import Wait


@Func
def wait_for(a):
    return Asm([a], [Wait()])


@Func
def Map(function, lst):
    # function is a symbol referring to a function, so must Apply it
    return If(
        Nullp(lst), [], Cons(Funcall(function, First(lst)), Map(function, Rest(lst))),
    )


@Func
def MapResolve(function, lst):
    """Map and then resolve all values"""
