"""Machine Probe"""


class Probe:
    """A machine debug probe"""

    def log(self, msg):
        pass

    def on_step(self, m):
        pass

    def on_run(self, m):
        pass

    def on_stopped(self, m):
        pass

    def on_return(self, m):
        pass

    def on_enter(self, m, fn_name: str):
        pass
