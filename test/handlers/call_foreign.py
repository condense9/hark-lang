from c9.lang import *
from c9.stdlib import *


@Foreign
def simple_math(x):
    return x - 1


@Func
def call_foreign(x):
    return Cons(simple_math(x), simple_math(x))


@Func
def main(x):
    # The rules:
    # - main will wait on the value returned
    # - you cannot wait on a list that contains futures
    # - the programmer must wait on all elements
    # SO this is illegal:
    #   return call_foreign(x)
    # ...because call_foreign returns a Cons of futures
    return Map(Wait, call_foreign(x))
