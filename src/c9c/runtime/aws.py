"""AWS Lambda run-time"""

from functools import wraps

from .. import compiler
from .. import machine as m


class AwsState(m.State):
    pass


class AwsProbe(m.Probe):
    pass


class AwsFuture(Future):
    pass


class AwsRuntime(m.Runtime):
    """AWS (lambda / ECS) runtime

    In AWS, there will be one Machine executing in the current context, and
    others executing elsewhere.

    """

    future_type = AwsFuture

    # def __init__

    # def run_machine(self, m):
    # def make_fork(self, fn_name, args):
    # def on_stopped(self, m):
    # def on_finished(self, result):
    # def get_future(self, m):


def run(executable, *args, do_probe=True):
    pass


def continue_from(executable, runtime):
    """Pick up execution from the given point"""


def get_entrypoint(handler):
    """Return a function that will run the given handler"""
    linked = compiler.link(compiler.compile_all(handler), entrypoint_fn=handler.label)

    @wraps(handler)
    def _f(event, context, linked=linked):
        state = LocalState([event, context])
        # FIXME
        machine.run(linked, state)
        return state.ds_pop()

    return _f
