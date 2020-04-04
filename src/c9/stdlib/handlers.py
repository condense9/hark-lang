"""Event handler decorators"""


from .. import lang as l
from ..lang import infrastructure as inf
from ..lang.func import FuncModifier


# This is tricky. We're building a new Foreign Node which takes some arguments
# at compile time, and some at runtime. Smart? Maybe not.
def Response(
    status: int, body, headers: dict = None, multi_value_headers: dict = None
) -> l.Foreign:
    if not headers:
        headers = {}

    if not multi_value_headers:
        multi_value_headers = {}

    @l.Foreign
    def _node(_status, _body, _headers, _mvh):
        # tryyy to detect content type at runtime
        if "content-type" not in headers:
            if isinstance(_body, dict):
                headers["content-type"] = "application/json"
                body = json.dumps(_body)
            else:
                headers["content-type"] = "text/html"

        return dict(
            statusCode=_status, body=_body, headers=_headers, multiValueHeaders=_mvh,
        )

    return _node(status, body, headers, multi_value_headers)


class HttpEndpoint(FuncModifier):
    """Add an HttpEndpoint infrastructure resource to func"""

    def __init__(self, method: str, path: str):
        self.method = method
        self.path = path

    def modify(self, fn: l.Func):
        name = self.method + "_" + self.path.replace("/", "_")
        fn.infrastructure.extend(
            [
                # The Endpoint handler is the Function name!
                inf.HttpEndpoint(name, self.method, self.path, name),
                inf.Function(name),
            ]
        )
        return fn
