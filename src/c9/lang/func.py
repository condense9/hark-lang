"""Decorators to make functions"""

import inspect
from .primitive import Quote, Funcall, ForeignCall, Node


class Func(Quote):
    """Represents a function - a DAG with symbolic bindings for values

    NOTE that this is a Quote! That is, a literal value.
    """

    blocking = True

    def __init__(self, fn, num_args=None, label=None):
        if label:
            self.label = label
        else:
            self.label = "F_" + fn.__name__
        super().__init__(self.label)
        sig = inspect.signature(fn)
        if num_args:
            self.num_args = num_args
        else:
            self.num_args = len(sig.parameters)
            for param in sig.parameters.values():
                if param.kind == param.VAR_POSITIONAL:
                    # Because the compiler needs to know the number of arguments to
                    # b_reduce. To be variadic the machine would need a bit of
                    # runtime logic.
                    raise Exception("Can't handle varargs (yet)")
        self.fn = fn
        self.constraints = None  # Unused for now.

    def __call__(self, *args):
        """Create a DAG node that calls this function with arguments"""
        return Funcall(self, *args, blocking=self.blocking)

    def b_reduce(self, values):
        """Evaluate the function with arguments replaced with values"""
        if len(values) != self.num_args:
            raise Exception(
                f"Wrong number of arguments - got {len(values)}, needed {self.num_args}"
            )
        # Not sure this is a good idea:
        result = self.fn(*values)
        if not isinstance(result, Node):
            result = Quote(result)
        return result

    @property
    def __name__(self):
        return self.fn.__name__

    def __repr__(self):
        return f"<Func {self.label}>"


class Foreign(Func):
    """Represents a foreign (native Python) function"""

    def __init__(self, fn):
        super().__init__(fn, label="FF_" + fn.__name__)
        self.fn = self._wrapper
        self.original_function = fn

    @property
    def __name__(self):
        return self.original_function.__name__

    def _wrapper(self, *args):
        return ForeignCall(self.original_function, *args)

    def __repr__(self):
        return f"<Foreign {self.label}>"


class AsyncFunc(Func):
    blocking = False


# FIXME - blocking is never passed to the ForeignCall node
class AsyncForeign(Foreign):
    blocking = False


class FuncModifier:
    """Abstract class to make decorators that create and modify Funcs"""

    def modify(self, fn: Func):
        raise NotImplementedError

    def __call__(self, fn):
        """Create a Func from fn, and modify it, or modify an existing Func"""
        func = fn if isinstance(fn, Func) else Func(fn)
        return self.modify(func)
