from c9c.lang import *
from c9c.stdlib import *
import random
import time


def random_sleep(max_ms=10):
    time.sleep(max_ms * random.random() / 1000.0)


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
    return Map(wait_for, call_foreign(x))
