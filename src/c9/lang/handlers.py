from . import FuncModifier
from . import infrastructure as inf


class HttpEndpoint(FuncModifier):
    """Add an HttpEndpoint infrastructure resource to func"""

    def __init__(self, method: str, path: str):
        self.method = method
        self.path = path

    def modify(self, fn):
        name = self.method + "_" + self.path.replace("/", "_")
        return inf.HttpEndpoint(name, self.method, self.path, fn.__name__)
