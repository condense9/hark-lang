"""Machine futures"""

import logging

from . import types as mt

LOG = logging.getLogger(__name__)


class Future:
    """A future - holds results of function calls"""

    def __init__(self, *, continuations=None, chain=None, resolved=False, value=None):
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
        if data.get("value", None):
            data["value"] = mt.TlType.deserialise(data["value"])
        return cls(**data)

    def __repr__(self):
        return f"<Future {id(self)} {self.resolved} ({self.value})>"


def _resolve_future(controller, vmid, value):
    """Resolve a machine future, and any dependent futures"""
    assert not isinstance(value, mt.TlFuturePtr)
    future = controller.get_future(vmid)

    future.resolved = True
    future.value = value
    if controller.is_top_level(vmid):
        controller.result = mt.to_py_type(value)
        controller.finished = True

    continuations = future.continuations
    if future.chain:
        continuations += _resolve_future(controller, future.chain, value)

    LOG.info("Resolved %d to %s. Continuations: %s", vmid, value, continuations)
    return continuations


def finish(controller, vmid, value) -> list:
    """Finish a machine, resolving its future

    Return waiting machines to invoke, and the value to invoke them with

    """
    if not isinstance(value, mt.TlFuturePtr):
        return value, _resolve_future(controller, vmid, value)

    # Otherwise, VALUE is another future, and we can only resolve this machine's
    # future if VALUE has also resolved. If VALUE hasn't resolved, we "chain"
    # this machine's future to it.
    next_future = controller.get_future(value)
    if next_future.resolved:
        return (
            next_future.value,
            _resolve_future(controller, vmid, next_future.value),
        )
    else:
        LOG.info("Chaining %s to %s", vmid, value)
        next_future.chain = vmid
        return None, []


def get_or_wait(controller, vmid, future_ptr):
    """Get the value of a future in the stack, or add a continuation

    Return tuple:
      - resolved (bool): whether the future has resolved
      - value: The data value, or None if not resolved
    """
    if not isinstance(future_ptr, mt.TlFuturePtr):
        raise TypeError(future_ptr)

    if type(vmid) is not int:
        raise TypeError(vmid)

    future = controller.get_future(future_ptr)

    if future.resolved:
        value = future.value
        LOG.info("%s has resolved: %s", future_ptr, value)
    else:
        LOG.info("%d waiting on %s", vmid, future_ptr)
        future.continuations.append(vmid)
        value = None

    return future.resolved, value
