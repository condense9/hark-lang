"""Synthesise into Serverless Components"""

import os
import warnings
from functools import partial
from typing import List

import yaml

from .. import infrastructure as inf
from .synthesiser import (
    DEFAULT_REGION,
    Synthesiser,
    SynthesisException,
    TextSynth,
    get_region,
    bijective_map,
    surjective_map,
)
from .synthstate import SynthState

FUNCTION_TYPE = "aws-lambda"


def indent_text(text, spaces=2):
    """Return text indented with the given number of spaces"""
    indent = " " * spaces
    return indent + text.replace("\n", f"\n{indent}")


class ServerlessComponent(Synthesiser):
    """Thin abstraction over Serverless Components"""

    def __init__(self, component_type: str, name: str, inputs: dict):
        self.component_type = component_type
        self.name = name
        self.inputs = inputs

    def yaml(self) -> str:
        """Create YAML for a Serverless ServerlessComponent"""
        return indent_text(
            yaml.dump({self.name: {"type": self.component_type, "inputs": self.inputs}})
        )

    def __repr__(self):
        return f"<ServerlessComponent {self.component_type} {self.name}>"

    ## generator interface (see synthstate.gen_iac):

    @property
    def filename(self) -> str:
        return "serverless.yaml"

    def generate(self) -> str:
        return self.yaml()


# Shared:
def get_sls_deploy_commands(state):
    """Get deployment commands for serverless"""
    if "serverless" in state.deploy_commands:
        return state.deploy_commands
    else:
        return state.deploy_commands + ["serverless"]


def make_function(state: SynthState, fn: inf.Function):
    return ServerlessComponent(
        FUNCTION_TYPE,
        fn.name,
        dict(
            code=state.code_dir,
            handler="main.event_handler",
            env=dict(C9_HANDLER=fn.name, C9_TIMEOUT=fn.timeout),
            memory=fn.memory,
            timeout=fn.timeout,
            runtime=fn.runtime,
            region=get_region(),
        ),
    )


def make_bucket(_, store: inf.ObjectStore):
    return ServerlessComponent(
        "aws-s3",
        store.name,
        dict(
            # --
            accelerated=store.accelerated,
            region=get_region(),
            cors=dict(CORSRules=store.cors_rules),
        ),
    )


def make_dynamodb(_, kvstore: inf.KVStore):
    return ServerlessComponent(
        "aws-dynamodb",
        kvstore.name,
        dict(
            region=get_region(),
            deletion_policy=kvstore.allow_deletion,
            attributeDefinitions=[
                dict(AttributeName=k, AttributeType=v) for k, v in kvstore.attrs.items()
            ],
            keySchema=[
                dict(AttributeName=k, KeyType=v) for k, v in kvstore.keys.items()
            ],
        ),
    )


def make_api(state, endpoints: List[ServerlessComponent]) -> ServerlessComponent:
    existing_functions = [
        c.name for c in state.iac if c.component_type == FUNCTION_TYPE
    ]

    # TODO check no duplicated endpoints (method + path)

    for e in endpoints:
        if e.handler not in existing_functions:
            # the "functions" synth must come before api
            raise SynthesisException(
                f"Can't find handler {e.handler} in IAC: {state.iac}"
            )

    api_endpoints = [
        dict(path=e.path, method=e.method, function=f"${{{e.handler}}}")
        for e in endpoints
    ]
    return ServerlessComponent(
        "api", "api", dict(region=get_region(), endpoints=api_endpoints),
    )


functions = partial(bijective_map, inf.Function, make_function)
buckets = partial(bijective_map, inf.ObjectStore, make_bucket)
dynamodbs = partial(bijective_map, inf.KVStore, make_dynamodb)
api = partial(surjective_map, inf.HttpEndpoint, make_api)


def finalise(state: SynthState) -> SynthState:
    # TODO any more glue? Permissions?
    resources = []

    existing = [c.name for c in state.iac if isinstance(c, ServerlessComponent)]

    # if not existing:
    #     return state

    if "c9_main" in existing:
        raise SynthesisException("Don't name an endpoint c9_main!")

    frontmatter = TextSynth(
        "serverless.yaml", f"name: {state.service_name}\n\ncomponents:\n"
    )
    c9_handler = ServerlessComponent(
        FUNCTION_TYPE,
        "c9_main",
        dict(
            code=state.code_dir,
            handler="main.c9_handler",  # TODO is this ok?
            memory=128,
            timeout=10,
            runtime="python3.8",
            region=get_region(),
        ),
    )

    # Push the C9 machine handler in and serverless component name
    iac = [frontmatter, c9_handler] + state.iac

    if "serverless" in state.deploy_commands:
        raise Exception("finalise called twice!")
    else:
        deploy_commands = state.deploy_commands + ["serverless"]

    return SynthState(
        state.service_name, resources, iac, deploy_commands, state.code_dir
    )
