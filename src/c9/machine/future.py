"""Machine futures"""

from . import types as mt
from .types import C9Type


class Future:
    """A future - holds results of function calls"""

    def __init__(self, continuations=None, chain=None, resolved=False, value=None):
        self.continuations = [] if not continuations else continuations
        self.chain = chain
        self.resolved = resolved
        self.value = value

    def serialise(self):
        value = self.value.serialise() if self.value else None
        return dict(
            continuations=self.continuations,
            chain=self.chain,
            resolved=self.resolved,
            value=value,
        )

    @classmethod
    def deserialise(cls, data):
        if data["value"]:
            data["value"] = C9Type.deserialise(data["value"])
        return cls(**data)


def _resolve_future(controller, vmid, value):
    """Resolve a machine future, and any dependent futures"""
    assert not isinstance(value, mt.C9FuturePtr)
    future = controller.get_future(vmid)

    with future.lock:
        future.resolved = True
        future.value = value
        if controller.is_top_level(vmid):
            controller.result = value
            controller.finished = True

        continuations = future.continuations
        if future.chain:
            continuations += _resolve_future(controller, future.chain, value)

    return continuations


def finish(controller, vmid, value) -> list:
    """Finish a machine, and return continuations (other waiting machines)"""
    if not isinstance(value, mt.C9FuturePtr):
        return value, _resolve_future(controller, vmid, value)

    # otherwise, check if the dependent future has resolved
    next_future = controller.get_future(vmid)
    with next_future.lock:
        if next_future.resolved:
            return (
                next_future.value,
                _resolve_future(controller, vmid, next_future.value),
            )
        else:
            next_future.chain = vmid


def get_or_wait(controller, vmid, future_ptr, offset):
    """Get the value of a future in the stack, or add a continuation

    Return tuple:
      - resolved (bool): whether the future has resolved
      - value: The data value, or None if not resolved
    """
    future = controller.get_future(future_ptr)
    # prevent race between resolution and adding the continuation
    with future.lock:
        resolved = future.resolved
        if resolved:
            value = future.value
        else:
            future.continuations.append((vmid, offset))
            value = None
    return resolved, value
