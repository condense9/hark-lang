"""Infrastructure"""
from dataclasses import dataclass as dc
from functools import wraps, partial, update_wrapper
from typing import List, Tuple

import yaml

from .compiler import compiler_utils
from .lang import Foreign, ForeignCall


# FIXME how to compile infrastructure references?
class Infrastructure:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<{type(self).__name__} {self.name}>"


################################################################################
## High level infrastructure dependencies
#
# These can be constrained - interface TBD.
#
# They are used to generate Serverless Components.


class Function(Infrastructure):
    def __init__(self, name, runtime="python3.8", memory=128, timeout=10):
        super().__init__(name)
        self.memory = memory
        self.timeout = timeout
        self.runtime = runtime


class HttpEndpoint(Infrastructure):
    def __init__(self, name, method, path, handler):
        super().__init__(name)
        self.method = method
        self.path = path
        self.handler = handler


class ObjectStore(Infrastructure):
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


class KVStore(Infrastructure):
    def __init__(
        self, name, attrs: dict, keys: dict, allow_deletion=False,
    ):
        super().__init__(name)
        self.keys = keys
        self.attrs = attrs
        self.allow_deletion = allow_deletion


# So there's an awkward restriction - you can't introduce bindings except by
# doing function calls. So multiple-value returns are out.
#
# success, todo = do_insert(...)
##=
# a = do_insert(...)  # -> List
# success = First(a)
# todo = Second(a)
#
# This isn't possible because the language can't express the "a = ..."


################################################################################
# Constructors


class InfrastructureRef(dict):
    pass


def make_infra_node(cls: Infrastructure, get_ref, *args, **kwargs) -> ForeignCall:
    # Note - the foreigncall can't take kwargs
    node = ForeignCall(get_ref, *args)
    node.infrastructure.append(cls(*args, **kwargs))
    return node


def make_reference(cls, attrs) -> InfrastructureRef:
    """Make a reference to infrastructure, retrieving some attributes"""
    # use cls name to find the attributes in the deployment state
    # return something that looks like cls


# Functions used with ForeignCall must
# http://louistiao.me/posts/adding-__name__-and-__doc__-attributes-to-functoolspartial-objects/
def wrapped_partial(func, *args, **kwargs):
    partial_func = partial(func, *args, **kwargs)
    update_wrapper(partial_func, func)
    return partial_func


# So ugly :(
ref_kvstore = partial(make_reference, KVStore, ["name"])
ref_kvstore.__name__ = "ref_kvstore"
ref_kvstore.__module__ = __name__

make_kvstore = partial(make_infra_node, KVStore, ref_kvstore)


################################################################################
# Things that work with refs


@Foreign
def db_scan(db: InfrastructureRef, args):
    print("scanning", item)


@Foreign
def db_insert(db: InfrastructureRef, args):
    print("inserting", item)
