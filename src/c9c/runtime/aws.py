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


@dataclass
class MachineRefs:
    state: int
    future: int


class AwsRuntime(m.Runtime):
    """AWS (lambda / ECS) runtime

    In AWS, there will be one Machine executing in the current context, and
    others executing elsewhere.

    There's a queue of "runnable machines".

    Run machine: push the new machine onto the queue.
    - At a fork
    - When a future resolves

    Stop: pop something from the queue and Start it

    Start top level: make a new machine and run it
    Start existing (fork or cont): take an existing stopped machine and run it

    """

    future_type = AwsFuture

    def __init__(self, executable, do_probe=False):
        self._executable = executable
        self.storage = AwsStorage()
        self._do_probe = do_probe

    def start_top_level(self, args):
        state = AwsState(*args)
        machine = self.storage.new_machine(state, probe)
        machine.probe.log(f"Top Level {machine}")
        self.storage.set_top_level(machine)
        return self._run_here(machine)

    def start_existing(self, machine):
        return self._run_here(machine)

    def _make_fork(self, fn_name, args):
        state = AwsState(*args)
        state.ip = self._executable.locations[fn_name]
        future = AwsFuture()
        probe = maybe_create(AwsProbe, self._do_probe)
        machine = self.storage.new_machine(state, probe)
        self.storage.set_future(machine, future)
        # -> stores the state, probe and future in a DB
        return machine, future


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
