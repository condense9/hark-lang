from c9 import *
import random
import time


def random_sleep(max_ms=10):
    time.sleep(max_ms * random.random() / 1000.0)


@AsyncForeign
def do_sleep(x):
    random_sleep()
    return x


@Foreign
def do_sleep_sync(x):
    random_sleep()
    return x


@Func
def level2(a, b):
    return Do(do_sleep_sync(a), do_sleep(a))


@AsyncFunc
def level1(a):
    return level2(a, a)


@Func
def main(a):
    return level1(a)
