import threading


class ThreadExecutor:
    def __init__(self, target):
        threading.excepthook = self._threading_excepthook
        self.exception = None
        self.target = target

    def _threading_excepthook(self, args):
        self.exception = args

    def run(self, *args):
        # Awkward - we have to pass in self to the target, as the executor has
        # to be the first argument. TODO - clean up this interface.
        t = threading.Thread(target=self.target, args=[self, *args])
        t.run()
