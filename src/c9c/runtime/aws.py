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

from functools import wraps

from .. import compiler
from .. import machine as m


class AwsProbe(m.Probe):
    pass


class AwsFuture(m.Future):
    def __init__(self, storage):
        super().__init__()
        # self.lock = threading.Lock()
        # self.continuations = []
        # todo

    def add_continuation(self, machine_reference, offset):
        pass  # todo


class MRef(int):
    pass


# TODO - what do I actually need to do with the DB?
# class DB:
# ...
#
# A session is created when a handler is first called. Multiple machines
# (threads) may exist in the session.
#
# Data per session:
# - machine state
# - probe logs
# - futures
#
# Data exchange points:
# - new session (create session id and top level machine)
# - new machine started (create state, probe)
# - machine continued (Controller retrieve state, probe)
# - machine forks (Controller uploads state, future, probe)
# - machine waits (Future adds continuation, something needs to sync)
# - top level machine finishes (Controller updates result)
# - future resolves (update state, run machine)
# - machine stops (sync state ?)


class AwsController(m.Controller):
    future_type = LocalFuture

    def __init__(self, executable, executor, do_probe=False):
        super().__init__()
        self._machine_future = {}
        self._machine_state = {}
        self._machine_probe = {}
        self._machine_idx = 0
        self._executor = executor
        self.executable = executable
        self.top_level = None
        self.result = None
        self.finished = False
        self.do_probe = do_probe

    def finish(self, result):
        pass  # todo

    def stop(self, machine):
        assert isinstance(machine, MRef)
        pass  # todo Could do something like sync the machine's state

    def is_top_level(self, machine):
        assert isinstance(machine, MRef)
        return machine == self.top_level

    def new_machine(self, args, top_level=False) -> MRef:
        pass  # todo

    def probe_log(self, m: MRef, msg):
        pass  # todo

    def get_future(self, m: MRef):
        pass  # todo

    def get_state(self, m: MRef):
        pass  # todo

    def get_probe(self, m: MRef):
        return AwsProbe(self.session_id,)

    def push_machine_to_run(self, m: MRef):
        pass  # todo

    @property
    def machines(self):
        pass  # todo

    @property
    def probes(self):
        return [self.get_probe(m) for m in self.machines]


def run(executable, *args, do_probe=True):
    pass


def continue_from(executable, runtime):
    """Pick up execution from the given point"""


# For auto-gen code:
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
