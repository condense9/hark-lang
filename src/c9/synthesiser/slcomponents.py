"""Synthesise into Serverless Components"""

import os
import yaml

from functools import partial
import warnings
from typing import List

from ..lang import infrastructure as inf
from .synthstate import SynthState
from .exceptions import SynthesisException

DEFAULT_REGION = "eu-west-2"


class ServerlessComponent:
    """Thin abstraction over Serverless Components"""

    def __init__(self, component_type: str, name: str, inputs: dict):
        self.component_type = component_type
        self.name = name
        self.inputs = inputs

    def yaml(self) -> str:
        """Create YAML for a Serverless ServerlessComponent"""
        return yaml.dump(
            {self.name: {"component": self.component_type, "inputs": self.inputs}}
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


def get_region():
    # Would be nice for this to be more easily configurable / obvious
    try:
        return os.environ["AWS_DEFAULT_REGION"]
    except KeyError:
        return DEFAULT_REGION


def _bijective_map(resource_type, f_inject, state: SynthState) -> SynthState:
    # f_inject :: SynthState -> resource_type -> ServerlessComponent
    resources = state.filter_resources(resource_type)
    if not resources:
        return state

    components = list(map(partial(f_inject, state), resources))

    existing = [c.name for c in state.iac if isinstance(c, ServerlessComponent)]
    for c in components:
        if c.name in existing:
            raise warnings.warn(f"{resource_type} {c.name} is already synthesised")

    return SynthState(
        # finalise will update the resources and deploy_command
        state.resources,
        state.iac + components,
        state.deploy_commands,
        state.code_dir,
    )


def _surjective_map(resource_type, f_map, state: SynthState) -> SynthState:
    # f_map :: SynthState -> [resource_type] -> ServerlessComponent
    resources = state.filter_resources(resource_type)
    if not resources:
        return state

    new_component = f_map(state, resources)

    # Each surjective map should only be called once...
    for c in state.iac:
        if c.component_type == new_component.component_type:
            raise warnings.warn(f"{c.component_type} is already synthesised")

    return SynthState(
        state.resources,
        state.iac + [new_component],
        state.deploy_commands,
        state.code_dir,
    )


def make_function(state: SynthState, fn: inf.Function):
    return ServerlessComponent(
        "function",
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
                dict(AttributeName=k[0], AttributeType=k[1]) for k in kvstore.attrs
            ],
            keySchema=[dict(AttributeName=k[0], KeyType=k[1]) for k in kvstore.keys],
        ),
    )


def make_api(state, endpoints: List[ServerlessComponent]) -> ServerlessComponent:
    existing_functions = [c.name for c in state.iac if c.component_type == "function"]

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


functions = partial(_bijective_map, inf.Function, make_function)
buckets = partial(_bijective_map, inf.ObjectStore, make_bucket)
dynamodbs = partial(_bijective_map, inf.KVStore, make_dynamodb)
api = partial(_surjective_map, inf.HttpEndpoint, make_api)


def finalise(state: SynthState) -> SynthState:
    # TODO any more glue? Permissions?
    resources = []

    existing = [c.name for c in state.iac if isinstance(c, ServerlessComponent)]

    # if not existing:
    #     return state

    if "c9_main" in existing:
        raise SynthesisException("Don't name an endpoint c9_main!")

    # Push the C9 machine handler in
    iac = state.iac + [
        ServerlessComponent(
            "function",
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
    ]

    if "serverless" in state.deploy_commands:
        raise Exception("finalise called twice!")
    else:
        deploy_commands = state.deploy_commands + ["serverless"]

    return SynthState(resources, iac, deploy_commands, state.code_dir)
