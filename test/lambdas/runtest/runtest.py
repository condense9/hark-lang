import glob
from os.path import dirname

import c9.controllers.ddb
import c9.executors.awslambda
import c9.machine.c9e
from c9 import Service
from c9.stdlib.handlers import HttpEndpoint

from . import *


def handler(event, context):
    run_method = c9.controllers.ddb.run_existing
    return c9.executors.awslambda.handler(run_method, event, context)


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
    include=["lib", *glob.glob(dirname(__file__) + "/*.py")]
    # outputs=[index_foo.endpoint_url],
)
