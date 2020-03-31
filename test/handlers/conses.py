from c9c.lang import *
from c9c.stdlib import *


@Foreign
def fn4(x):
    return x + 2


async_f4 = Async(fn4)


@Foreign
def fn3(x):
    return x + 1


@Foreign
def fn2(x):
    return x


@Func
def main(x):
    return List(1, fn2(x), fn3(x), fn4(x))
