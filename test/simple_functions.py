import time
import random
from random import randint


def plus1(x):
    return x + 1


def times2(x):
    time.sleep(randint(1, 3))
    return x * 2


def times3(x):
    time.sleep(randint(1, 3))
    return x * 3


def sum_two(a, b):
    return a + b


def printit(arg):
    print(arg)


def random_sleep_math(x):
    time.sleep(random.random()/10.0)
    return (2 * x) + 3


class Buf:
    def __init__(self):
        self.output = ""

    def puts(self, val):
        self.output += f"{val}\n"
