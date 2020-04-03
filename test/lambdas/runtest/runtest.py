import c9.controllers.ddb
import c9.executors.awslambda
import c9.machine.c9e
from c9 import Service

from . import *


def handler(event, context):
    run_method = c9.controllers.ddb.run_existing
    return c9.executors.awslambda.handler(run_method, event, context)


SERVICE = Service(
    name="foo",
    handlers=[
        ("all_calls", all_calls.main),
        ("mapping", mapping.main),
        ("call_foreign", call_foreign.main),
        ("series_concurrent", series_concurrent.main),
        ("conses", conses.main),
    ],
    # outputs=[index_foo.endpoint_url],
)
