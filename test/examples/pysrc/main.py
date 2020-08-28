import time
import random


def hi():
    return "Hi Hark!"


def format(x, *args):
    return x.format(*args)


def random_sleep(min_ms=10, max_ms=1000):
    """Sleep for some random time between MIN_MS and MAX_MS"""
    duration_ms = min_ms + random.random() * (max_ms - min_ms)
    # Note that this output won't appear in Hark's standard output. This may
    # change in future.
    print(f"python sleeping {duration_ms:.0f}ms")
    time.sleep(duration_ms / 1000.0)


def coin():
    """Randomly return True or False"""
    return random.random() > 0.5


def bad_fn():
    raise Exception("Something broke!")
