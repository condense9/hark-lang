"""Shared utilities"""


def maybe_create(cls, cond):
    if cond:
        return cls()
    else:
        return None
