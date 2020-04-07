import glob
from os.path import dirname

from c9 import Service
from c9.stdlib.handlers import HttpEndpoint

from . import all_calls, call_foreign, conses, mapping, series_concurrent


@HttpEndpoint("GET", "/foo")
def foo(a):
    return a


SERVICE = Service(
    name="foo",
    handlers=[
        ("foo", foo),
        ("all_calls", all_calls.main),
        ("mapping", mapping.main),
        ("call_foreign", call_foreign.main),
        ("series_concurrent", series_concurrent.main),
        ("conses", conses.main),
    ],
    include=[*glob.glob("lib/*"), *glob.glob(dirname(__file__) + "/*.py")],
    # outputs=[index_foo.endpoint_url],
)
