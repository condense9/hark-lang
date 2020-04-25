from c9.lang import *
import random
import time


def random_sleep(min_ms=1000, max_ms=5000):
    duration = max(min_ms, max_ms * random.random()) / 1000.0
    print("sleeping", duration)
    time.sleep(duration)


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
