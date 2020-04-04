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

"""

from os import makedirs
from os.path import abspath, basename, dirname, join, splitext
from shutil import copy, copytree, rmtree
from typing import List

from . import infrastructure as inf
from . import lang as l
from .compiler_utils import flatten, traverse_dag

# Synthesis:
# - take a handler
#
# - traverse the entire handler DAG
#
# - ignore any more Handlers encountered - they'll be done separately (TODO
#   think abou the implications of this)
#
# - if there are any Infrastructure Nodes, record them as dependencies of this
# - handler.
#
# - Given a set of l.Infrastructure, e.g. one might be "Machine", generate
# - serverless components (and other files) that implement it. This will have to
# - be very abstract - e.g. it just gets a build directory.
#
# - Return the infrastructure that the handler requires (will be new), plus any
# - other dependencies (may be reused elsewhere)


# Implementation:
# - take some abstract infrastructure pieces as a graph
# - generate the serverless components to implement the infrastructure


# Steps
# 1. Compilation :: Source -> Handlers
# 3. Synthesis :: Handlers -> Infrastructure Dependencies + Executables
# 4. Implementation :: infrastructure deps -> Cloud Resources
# 5. Generation :: Executables + Cloud Resources -> Deployment Package
#
# Constraints may be specified at any step. How?


def entrypoint_for(handler):
    fn_prefix = "handler_"
    return f"{fn_prefix}{handler.label}"


def synthesise(service, region, code_dir):
    explicit = {}
    implicit = []
    endpoints = []
    api = inf.Api(region)

    for handler in service.handlers:
        for resource in handler.infrastructure:
            if isinstance(resource, inf.HttpEndpoint):
                implicit.append(
                    inf.Function(
                        resource.name, code_dir, "main." + entrypoint_for(handler)
                    )
                )
                api.add_endpoint(resource)
            else:
                raise NotImplementedError

        # Literal (Quote) infrastructure
        for node in traverse_dag(handler):
            if isinstance(node, l.Infrastructure) and node not in explicit:
                explicit[n] = n.synthesise()

    if api.endpoints:
        implicit.append(api)

    return implicit + list(explicit.values())


# TODO break up this function
def generate(service, build_dir):
    # Call this from the top-level file
    # Generates:
    # build_dir/serverless.yml
    # build_dir/code/main.py
    # build_dir/code/c9c/
    # build_dir/code/src/

    code_dir = "./code"
    region = "eu-west-2"

    top_level_file = abspath(service.entrypoint)
    top_level_module = splitext(basename(service.entrypoint))[0]
    assert top_level_file.endswith(".py")

    makedirs(join(build_dir, code_dir, "src"))

    # -- build_dir/handlers/src/...
    print(top_level_file)
    copy(top_level_file, join(build_dir, code_dir, "src"))
    # if extra_source: TODO copy extra dirs to handlers/src

    # -- build_dir/serverless.yml
    components = synthesise(service, region, code_dir)
    with open(join(build_dir, "serverless.yml"), "w") as fp:
        fp.write(f"name: {service.name}\n")
        for c in components:
            fp.write("\n")
            fp.write(c.yaml())

    # -- build_dir/code_dir/main.py
    with open(join(build_dir, code_dir, "main.py"), "w") as fp:
        fp.write("import c9.runtimes.awslambda as awslambda\n\n")
        for h in service.handlers:
            fp.write("\n")
            entrypoint = entrypoint_for(h)
            implementation = h.fn.__name__
            fp.write(f"from src.{top_level_module} import {implementation}\n")
            # Entrypoints to different runtimes could be implemented, and used
            # depending on constraints. For now, always use awslambda.
            fp.write(f"{entrypoint} = awslambda.get_entrypoint({implementation})\n")

    # -- build_dir/code_dir/c9c
    copytree(dirname(__file__), join(build_dir, code_dir, "c9c"))

    # -- TODO requirements


# Generate:
# from src.service import foo
# run_from_foo = run_from(foo)
