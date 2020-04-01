import threading


class ThreadExecutor:
    def __init__(self, target):
        threading.excepthook = self._threading_excepthook
        self.exception = None
        self.target = target

    def _threading_excepthook(self, args):
        self.exception = args

    def run(self, *args):
        t = threading.Thread(target=self.target, args=args)
        t.run()
