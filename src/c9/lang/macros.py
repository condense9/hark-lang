"""Macros!!!!!!111!"""

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
