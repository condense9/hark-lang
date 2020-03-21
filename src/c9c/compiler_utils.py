"""Shared utilities"""

import lang as l
import itertools
from collections import deque


def flatten(list_of_lists: list) -> list:
    "Flatten one level of nesting"
    return list(itertools.chain.from_iterable(list_of_lists))


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)


def map_funcs(fn: l.Func, mapping_fn) -> dict:
    """Apply MAPPING_FN to every Func in FN

    Return {x.label: mapping_fn(x) for x::Func in range(fn)}
    """
    domain = deque([fn])
    result = {}

    while domain:
        this_fn = domain.pop()

        body, calls = mapping_fn(this_fn)

        result[this_fn.label] = body

        for c in calls:
            if c not in domain:
                domain.append(c)

    return result
