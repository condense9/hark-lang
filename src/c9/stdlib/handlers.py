"""Event handler decorators"""


from .. import lang as l
from .. import infrastructure as inf


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


class HttpHandler:
    def __init__(self, method, path):
        self.method = method
        self.path = path

    def __call__(self, fn):
        # TODO check at compile-time that the wrapped function takes (event,
        # context) ??
        # TODO handle wrapping another Handler (append infrastructure)
        name = fn.__qualname__.replace(".", "__")
        endpoint = inf.HttpEndpoint(name, self.method, self.path)
        return l.Handler(fn, [endpoint])
