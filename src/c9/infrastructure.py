"""InfrastructureNode"""
from dataclasses import dataclass as dc
from functools import partial, update_wrapper, wraps
from types import SimpleNamespace
from typing import List, Tuple

import yaml

from .compiler import compiler_utils
from .lang import Foreign, ForeignCall
from .synthesiser import outputs


class Infrastructure:
    """Rrepresents general purpose Infrastructure"""

    runtime_attributes = []
    _used_names = []

    @staticmethod
    def make_name(inst, name):
        full_name = f"{type(inst).__name__}_{name}"

        # Commented out - seems like it causes issues on Lambda...
        # if full_name in Infrastructure._used_names:
        #     raise ValueError(full_name)
        # Infrastructure._used_names.append(full_name)

        return full_name

    def __init__(self, name, *args, **kwargs):
        self.infra_name = Infrastructure.make_name(self, name)
        self.infra_spec = SimpleNamespace(**self.init_spec(name, *args, **kwargs))

    def __repr__(self):
        return f"<Infrastructure {self.infra_name}>"


class InfrastructureNode(ForeignCall):
    """Represents Infrastructure that can be used as a Node in the DAG

    This is a foreigncall! At run-time, `load_outputs` is called with the
    infrastructure name, and the result will be a dict of attributes that user
    code can use to access the resource.
    """

    runtime_attributes = []

    def __init__(self, name, *args, **kwargs):
        self.infra_name = Infrastructure.make_name(self, name)
        self.infra_spec = SimpleNamespace(**self.init_spec(name, *args, **kwargs))

        # load_outputs is the foreign function!
        super().__init__(outputs.load_infra_outputs, self.infra_name)

    def __hash__(self):
        return hash(self.infra_name)

    def __repr__(self):
        return f"<InfrastructureNode {self.infra_name}>"


################################################################################
# Define some Infrastructure!
#
# NOTE that the synthesisers must be written in conjunction so that the runtime
# attributes are correctly written for each type. Only relevant for
# InfrastructureNode classes.


# class HttpEndpointPath:
#     def __init__(self, url, query, body)


class HttpEndpoint(Infrastructure):
    def init_spec(self, name, method, path, handler, path_params, body_params):
        # query and body: dict { param_name -> param_type }
        # TODO optional params
        if not path_params:
            path_params = {}
        if not body_params:
            body_params = {}
        return dict(
            name=name,
            method=method,
            path=path,
            handler=handler,
            body_params=body_params,
            path_params=path_params,
            query_params={},
        )


class Function(Infrastructure):
    def init_spec(self, name, runtime="python3.8", memory=128, timeout=10):
        return dict(name=name, runtime=runtime, memory=memory, timeout=timeout)


class KVStore(InfrastructureNode):
    runtime_attributes = ["id"]

    def init_spec(self, name, attrs: dict, keys: dict, allow_deletion=False) -> dict:
        return dict(name=name, attrs=attrs, keys=keys, allow_deletion=allow_deletion)


class ObjectStore(InfrastructureNode):
    runtime_attributes = ["name"]

    def init_spec(
        self,
        name,
        acl="private",
        accelerated=False,
        cors_rules=None,
        allowed_origins=None,
    ):
        """An object store.

        accelerated: enable upload acceleration for S3 buckets

        If cors_rules is unset, a default set of cors rules are used. If
        allowed_origins is set, the AllowedOrigins property will use it

        """
        if not cors_rules:
            cors_rules = dict(
                AllowedHeaders=["*"],
                AllowedMethods=["PUT", "POST", "DELETE"],
                AllowedOrigins=[],
                MaxAgeSeconds=3000,
            )
            if allowed_origins:
                cors_rules["AllowedOrigins"] = allowed_origins

        return dict(name=name, accelerated=accelerated, acl=acl, cors_rules=cors_rules)
