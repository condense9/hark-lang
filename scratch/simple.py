from lang import *


def plus1(x):
    return x + 1


def times2(x):
    return x * 2


def cube(x):
    return x ** 3


@defun
def times2_and_plus1(x):
    return Sysop(times2, Sysop(plus1, x))


@defun
def simple_prog(foo):
    temp = times2_and_plus1(foo)
    return Sysop(cube, temp)


@defun
def simple_cond(foo):
    # How to capture variables? Scoping is hard...
    a = Sysop(lambda x: x > 10, foo)
    b = Sysop(lambda x: x * 2, foo)
    c = Sysop(lambda x: x / 2, foo)
    return If(a, b, c)


@defun
def conc_prog(a, b):
    a_ = times2_and_plus1(a, concurrent=True)
    b_ = times2_and_plus1(b, concurrent=True)
    return Sysop(lambda a, b: a + b, a_, b_)


if __name__ == "__main__":
    # eval_with(simple_prog("foo"), lambda n: print(n, n.operands), maxdepth=2)
    # print(to_dot(simple_prog("foo")))
    # visit(simple_cond("foo"), lambda n: print(n))
    # print("\n".join(fn_dot(simple_prog)))
    # print(to_dot(simple_prog))
    print(simple_prog("foo").operands)
