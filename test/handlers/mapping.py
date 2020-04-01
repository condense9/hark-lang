from c9.lang import *
from c9.stdlib import *
import random
import time


def random_sleep(max_ms=10):
    time.sleep(max_ms * random.random() / 1000.0)


@Foreign
def random_sleep_math(x):
    random_sleep()
    return (2 * x) + 3


@Func
def main(a):
    return MapResolve(random_sleep_math, a)
