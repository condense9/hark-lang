import time
import random


def format(x, *args):
    return x.format(*args)


def random_sleep(min_ms=10, max_ms=1000):
    duration_ms = min_ms + random.random() * (max_ms - min_ms)
    print(f"python sleeping {duration_ms:.0f}ms")
    time.sleep(duration_ms / 1000.0)
