"""Shared utilities"""

import itertools
from collections import deque

from . import lang as l


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def traverse_dag(fn: l.Func):
    """Yield every node in the DAG, starting from FN"""
    to_visit = deque([fn])
    visited = []

    while to_visit:
        this_fn = to_visit.pop()
        visited.append(this_fn)

        yield this_fn

        # Reduce the function with symbolic placeholders, and continue traversal
        placeholders = [l.Symbol(i) for i in range(this_fn.num_args)]
        node = this_fn.b_reduce(placeholders)

        for n in node.descendents:
            if n not in visited:
                if isinstance(n, l.Func):
                    to_visit.append(n)
                else:
                    yield n
