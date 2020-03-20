"""Node -> Infrastructure

Only Funcall can have infrastructure attached to it. In the base case, it just
has a Lambda function, and whatever triggers it.

Trigger:

- either it is called by another function (so it's just a normal
  SNS/SQS/whatever triggering mechanism we use in that Backend), OR

- it's some other cloud event, which is special infrastructure


If you build a custom function, you can specify how

@Func
@add_infrastructure(backend.ObjectStore(...))
def post_to_object_store(bucket, request):


You can reference infrastructure - so there's a particular Node type, or a
normal Quote with some metadata, which describes that infrastructure.

class ObjectStore(Quote)

Maybe that stuff goes into infrastructure.py, and this file generates the SC
YAML files..


You can also build triggers - these are decorators have infrastructure, and can
be applied to Func.


class http_post:
    def __call__():
        return Func...

"""

from typing import List

import infrastructure as inf
import lang as l
from compiler_utils import map_funcs, flatten


@singledispatch
def synthesise_node(node: l.Node) -> CodeObject:
    """Take an AST node and (recursively) synthesise infrastructure"""
    raise NotImplementedError(node, type(node))


################################################################################
## Entrypoints


def synthesise_all(fn: l.Func) -> List[inf.Infrastructure]:
    """Generate infrastructure for FN and all of its dependencies"""
    synths = map_funcs(fn, synthesise_function)
    return flatten(synths.values())


def synthesise_function(
    fn: l.Func, backend
) -> Tuple[List[inf.Infrastructure], List[l.Func]]:
    """Generate infrastructure for function"""
    out = synthesise_node(node)

    calls = []
    new_nodes = node.descendents
    for n in new_nodes:
        if isinstance(n, l.Func) and n not in calls:
            calls.append(n)

    return out, calls
