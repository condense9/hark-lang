"""Infrastructure"""
import yaml
from dataclasses import dataclass as dc
from typing import List, Tuple


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
    def __init__(self, name, accelerated=False, cors_rules=None, allowed_origins=None):
        """An object store.

        accelerated: enable upload acceleration for S3 buckets

        If cors_rules is unset, a default set of cors rules are used. If
        allowed_origins is set, the AllowedOrigins property will use it

        """
        super().__init__(name)
        self.accelerated = accelerated
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
        self,
        name,
        attrs: List[Tuple[str, str]],
        keys: List[Tuple[str, str]],
        allow_deletion=False,
    ):
        super().__init__(name)
        self.key_schema = key_schema
        self.attributes = attributes
        self.allow_deletion = allow_deletion
