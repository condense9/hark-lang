"""Standard library of utilities"""

from .. import lang as l
from .. import machine as m
from ..lang import Asm, AsyncFunc, Foreign, ForeignCall, Func, Funcall, If

## This is awkward - these are builtins, but we define them as functions so that
## they can be used like normal functions


@Func
def Eq(a, b):
    return Asm([a, b], [m.Eq()])


@Func
def Atomp(a):
    return Asm([a], [m.Atomp()])


@Func
def Cons(a, b):
    return Asm([a, b], [m.Cons()])


@Func
def First(a):
    return Asm([a], [m.First()])


@Func
def Rest(a):
    return Asm([a], [m.Rest()])


@Func
def Nullp(a):
    return Asm([a], [m.Nullp()])


@Func
def Wait(a):
    return Asm([a], [m.Wait(0)])


## End of builtins

# List utils


@Func
def Nth(n, lst):
    # NOTE it's *wrong* to use an FCALL in a built-in language function... but
    # this is MVP :)
    return If(Eq(n, 0), First(lst), Nth(ForeignCall(lambda x: x - 1, x), Rest(lst)))


@Func
def Second(lst):
    return Nth(1, lst)


@Func
def Third(lst):
    return Nth(2, lst)


@Func
def Fourth(lst):
    return Nth(3, lst)


# Aliases
Car = First
Cdr = Rest
Cadr = Second
Caddr = Third
Cadddr = Fourth


##

# List utils

# Cheating here...
@Foreign
def Len(lst):
    return len(lst)


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
def Foldr(function, final, lst):
    """Fold (reduce) lst with function, from left-to-right

    -- foldr f z []     = z
    -- foldr f z (x:xs) = f x (foldr f z xs)
    """
    return If(
        # --
        Nullp(lst),
        final,
        Funcall(function, First(lst), Foldr(function, final, Rest(lst))),
    )


@Func
def WaitAll(lst):
    return Map(Wait, lst)


@Func
def MapResolve(function, lst):
    """Map and then resolve all values"""
    return WaitAll(Map(function, lst))


## Misc:


def List(*args):
    """Shorthand for a nested cons"""
    return Asm(list(args), [m.Cons() for _ in range(len(args) - 1)])


# I think varargs can be easily implemented now that List exists.
#
# class VarCallable:
#     def __init__(self, fn, n):
#         self._fn = fn
#         self._n = n
#         self.__name__ = f"__VA_{fn.__name__}_{n}"
#     def __call__(self, *args):
#         return self._fn(args)
#
#
# def VarFunc(fn):
#     def _wrapper(*args):
#         n = len(args)
#         return Func(VarCallable(fn, n), n)(*args)
#     return _wrapper
#
# Could also implement an "Async" function which returns an AsyncFunc version of
# the Func it's called with.
