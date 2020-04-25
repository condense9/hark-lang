import time
import random


def hi():
    print("Hi from python!")


def format(string, *args):
    return string.format(*args)


def sleep(duration):
    time.sleep(duration)


def random_sleep(min_ms=1000, max_ms=2000):
    duration = max(min_ms, max_ms * random.random()) / 1000.0
    print("python sleeping", duration)
    time.sleep(duration)
