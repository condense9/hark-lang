import time


def hi():
    print("Hi from python!")


def format(string, *args):
    return string.format(*args)


def sleeper():
    time.sleep(0.5)