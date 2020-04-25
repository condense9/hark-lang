"""Machine futures"""


class ChainedFuture:
    """A chainable future

    TODO document interface. See chain_resolve and LocalFuture for now.

    """


# This should probably be a ChainedFuture class method
def chain_resolve(future: ChainedFuture, value, run_waiting_machine) -> bool:
    """Resolve a future, and the next in the chain, if any"""
    actually_resolved = True

    with future.lock:
        if isinstance(value, ChainedFuture):
            if value.resolved:
                value = value.value  # pull the value out of the future
            else:
                actually_resolved = False
                value.chain = future

        if actually_resolved:
            future.resolved = True
            future.value = value
            if future.chain:
                chain_resolve(future.chain, value, run_waiting_machine)
            for machine, offset in future.continuations:
                run_waiting_machine(machine, offset, value)

    return actually_resolved, value
