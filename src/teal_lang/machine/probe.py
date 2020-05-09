"""Machine Probe"""

import time


class Probe:
    """A machine debug probe"""

    count = 0

    def __init__(self, *, max_steps=None):
        """Create the probe

        If max_steps is not None, the machine will be halted if execution steps
        exceeds max_steps

        """
        self._max_steps = max_steps
        self.steps = 0
        Probe.count += 1
        self._name = f"P{Probe.count}"
        self.logs = []
        self.events = []
        self.early_stop = False

    @classmethod
    def with_logs(cls, logs):
        probe = cls()
        probe.logs = logs
        return probe

    @property
    def serialised_events(self):
        return self.events

    def event(self, etype: str, **data):
        now = time.time()
        self.events.append(dict(time=now, event=etype, data=data))

    def on_run(self, m):
        self.event("run")
        self.log(f"! {m.vmid} Starting")

    def log(self, text):
        self.logs.append(f"*** <{self._name}> {text}")

    def on_enter(self, m, fn_name: str):
        self.event("call", fn_name=fn_name)
        self.log(f"===> {fn_name}")

    def on_return(self, m):
        self.event("return")
        self.log(f"<===")

    def on_step(self, m):
        self.steps += 1
        preface = f"[step={self.steps}, ip={m.state.ip}] {m.instruction}"
        data = list(m.state._ds)
        self.log(f"{preface:40.40} | {data}")
        if self._max_steps and self.steps >= self._max_steps:
            self.log(f"MAX STEPS ({self._max_steps}) REACHED!! ***")
            self.early_stop = True
            m.state.stopped = True

    def on_stopped(self, m):
        kind = "Terminated" if m.terminated else "Stopped"
        self.event("stop")
        self.logs.append(f"*** <{self._name}> {kind} after {self.steps} steps. ***")
        self.logs.append(m.state.to_table())
