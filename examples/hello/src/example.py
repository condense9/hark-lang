import time
import random


def hi():
    print("Hi from python!")


def format(string, *args):
    return string.format(*args)


def sleep(duration):
    time.sleep(duration)


def random_sleep(min_ms=10, max_ms=1000):
    duration_ms = min_ms + random.random() * (max_ms - min_ms)
    print(f"python sleeping {duration_ms:.0f}ms")
    time.sleep(duration_ms / 1000.0)
