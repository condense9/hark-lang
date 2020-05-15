importpy format from pysrc.main
importpy cos from math


def show_format(name):
    format("Hello {}!", name)


def show_trig(val):
    cos(val)


def main():
    print(show_format("World!"))
    print("Cos(0.0):")
    print(show_trig(0))
