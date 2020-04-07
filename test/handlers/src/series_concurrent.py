from c9.lang import *
import random
import time


def random_sleep(max_ms=10):
    time.sleep(max_ms * random.random() / 1000.0)


@Foreign
def a(x):
    random_sleep()
    return x + 1


@Foreign
def b(x):
    random_sleep()
    return x * 1000


@Foreign
def c(x):
    random_sleep()
    return x - 1


@Foreign
def d(x):
    random_sleep()
    return x * 10


@Foreign
def h(u, v):
    return u - v


@Func
def main(x):
    return h(b(a(x)), d(c(x)))  # h(x) = (1000 * (x + 1)) - (10 * (x - 1))
