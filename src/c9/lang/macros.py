"""Macros!!!!!!111!

These are decorators to modify the result of calling a Func. They are
compile-time AST modifiers. Pre-compiler optimisation. Happy days.

Given a Func, fn, called with some args, the result will be a Node (a).

Node (a) is passed to the macro tfm (transform) function.

tfm must return a Node (b).

Node (b) is substituted (i.e. at compile-time) into where the original Node
would have been.

"""

# TODO!

from .func import Func

# A macro takes a node and modifies it.


class Macro:
    def __init__(self, label):
        self.label = label

    def __call__(trs):
        """Return a decorator to modify a Func"""

        def _decorator(self, fn):
            _fn = Func(fn)

            def _call(self, *args):
                node = _fn(*args)
                return trs(node)

            label = self.label.format(fn.__name__)
            return Func(_call, num_args=_fn.num_args, label=label)

        return _decorator


@Macro(label="FF_{}")
def Foreign(node: Funcall):
    def _wrapper(self, *args):
        return ForeignCall(node.fn, *node.operands)

    return Func(_wrapper, blocking=node.blocking, label="FF_" + node.label)


@Foreign
def foo(x):
    return x + 1


## Func Modifiers
