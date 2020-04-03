"""Decorators to make functions"""

import inspect
from .primitive import Quote, Funcall, ForeignCall


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

    def unquote(self):
        # the "machine representation" of a function is just it's name.
        return self.label

    def b_reduce(self, values):
        """Evaluate the function with arguments replaced with values"""
        if len(values) != self.num_args:
            raise Exception(
                f"Wrong number of arguments - got {len(values)}, needed {self.num_args}"
            )
        return self.fn(*values)

    @property
    def __name__(self):
        return self.fn.__name__

    def __repr__(self):
        return f"<Func {self.label}>"


class Foreign(Func):
    """Represents a foreign (native Python) function"""

    def __init__(self, fn):
        super().__init__(fn)
        self.label = "FF_" + fn.__name__
        self.fn = self._wrapper
        self.original_function = fn

    def _wrapper(self, *args):
        return ForeignCall(self.original_function, *args)

    def __repr__(self):
        return f"<Foreign {self.label}>"


class AsyncFunc(Func):
    blocking = False


# FIXME - blocking is never passed to the ForeignCall node
class AsyncForeign(Foreign):
    blocking = False


class Handler(Func):
    """A special kind of Func that includes some infrastructure"""

    def __init__(self, fn, infrastructure):
        super().__init__(fn)
        self.infrastructure = infrastructure
