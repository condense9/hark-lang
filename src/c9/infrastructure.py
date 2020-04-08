"""InfrastructureNode"""
from dataclasses import dataclass as dc
from functools import partial, update_wrapper, wraps

# class DynamoDB(Constructor):
#     def __init__(self, name, **kwargs):
#         super().__init__(self)
#         self.infrastructure.append[]
#     def construct(self, )
from types import SimpleNamespace
from typing import List, Tuple

import yaml

from . import synthesiser
from .compiler import compiler_utils
from .lang import Foreign, ForeignCall

# FIXME how to compile infrastructure references?
# class InfrastructureNode:
#     def __init__(self, name):
#         self.name = name

#     def __repr__(self):
#         return f"<{type(self).__name__} {self.name}>"


################################################################################
## High level infrastructure dependencies
#
# These can be constrained - interface TBD.
#
# They are used to generate Serverless Components.


# class HttpEndpoint:
#     def __init__(self, name, method, path, handler):
#         # super().__init__(name)
#         self.method = method
#         self.path = path
#         self.handler = handler


class ObjectStore:
    def __init__(
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
        super().__init__(name)
        self.accelerated = accelerated
        self.acl = acl
        if cors_rules:
            self.cors_rules = cors_rules
        else:
            self.cors_rules = dict(
                AllowedHeaders=["*"],
                AllowedMethods=["PUT", "POST", "DELETE"],
                AllowedOrigins=[],
                MaxAgeSeconds=3000,
            )
            if allowed_origins:
                self.cors_rules["AllowedOrigins"] = allowed_origins


class Infrastructure:
    """Rrepresents general purpose Infrastructure"""

    runtime_attributes = []
    _used_names = []

    @staticmethod
    def make_name(inst, name):
        full_name = f"{type(inst).__name__}_{name}"

        if full_name in Infrastructure._used_names:
            raise ValueError(full_name)

        Infrastructure._used_names.append(full_name)
        return full_name

    def __init__(self, name, *args, **kwargs):
        self.infra_name = Infrastructure.make_name(self, name)
        self.infra_spec = SimpleNamespace(**self.init_spec(name, *args, **kwargs))

    def __repr__(self):
        return f"<Infrastructure {self.infra_name}>"


class InfrastructureNode(ForeignCall):
    """Represents Infrastructure that can be used as a Node in the DAG

    (And referred to at runtime)
    """

    runtime_attributes = []

    def __init__(self, name, *args, **kwargs):
        self.infra_name = Infrastructure.make_name(self, name)
        self.infra_spec = SimpleNamespace(**self.init_spec(name, *args, **kwargs))

        # This is a foreigncall!
        super().__init__(synthesiser.load_outputs, self.infra_name, name)

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


class HttpEndpoint(Infrastructure):
    def init_spec(self, name, method, path, handler):
        return dict(name=name, method=method, path=path, handler=handler)


class Function(Infrastructure):
    def init_spec(self, name, runtime="python3.8", memory=128, timeout=10):
        return dict(name=name, runtime=runtime, memory=memory, timeout=timeout)


class KVStore(InfrastructureNode):
    runtime_attributes = ["name"]

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
