from c9c.lang import *
from c9c.stdlib import *


@Foreign
def fn4(x):
    return x + 2


@AsyncFunc
def async_fn4(x):
    return fn4(x)


@Foreign
def fn3(x):
    return x + 1


@Foreign
def fn2(x):
    return x


@Func
def main(x):
    return WaitAll(List(1, fn2(x), fn3(x), async_fn4(x)))
