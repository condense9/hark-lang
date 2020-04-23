"""Top level syntax sugar"""

from .compiler import compile_all, link


def compile_handler(handler):
    """Compile a handler"""
    return link(compile_all(handler), handler.__name__, entrypoint_fn=handler.label)
