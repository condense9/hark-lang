"""Shared utilities"""

import logging
import itertools
from collections import deque

from .. import lang as l


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def traverse_dag(fn: l.Func, only=None):
    """Yield every Node and Func in the DAG, starting from FN"""
    to_visit = deque([fn])
    visited = []

    while to_visit:
        this_fn = to_visit.pop()
        visited.append(this_fn)

        if not isinstance(this_fn, l.Func):
            raise Exception(f"{this_fn} is not Func (bad compile tree)")

        if not only or isinstance(this_fn, only):
            yield this_fn

        # Reduce the function with symbolic placeholders, and continue traversal
        placeholders = [l.Symbol(i) for i in range(this_fn.num_args)]
        node = this_fn.b_reduce(placeholders)

        for n in node.descendents:
            if n not in visited:
                if isinstance(n, l.Func):
                    to_visit.append(n)
                else:
                    if not isinstance(n, l.Node):
                        raise Exception(f"{n} is not Node (bad compile tree)")
                    if not only or isinstance(n, only):
                        yield n


def traverse_fn(fn: l.Func):
    to_visit = deque([fn])
    nodes = []
    logging.info("Top Node: %s", str(fn))

    while to_visit:
        this_node = to_visit.pop()

        for n in this_node.operands:
            logging.info("Node: %s", str(n))
            if n not in nodes:
                nodes.append(n)
            if isinstance(n, (l.Funcall, l.ForeignCall, l.If, l.Do, l.Asm)):
                # if not isinstance(n, (l.Func)):
                to_visit.append(n)

    return nodes
