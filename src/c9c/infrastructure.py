"""Infrastructure

The output of synthesiser.py

Actually generate infrastructure.

Infrastructure doesn't reference functions; functions reference infrastructure
(by composition).

"""
import yaml
from dataclasses import dataclass as dc
from typing import List

from . import lang as l


################################################################################
## High level infrastructure dependencies
#
# These can be constrained - interface TBD.
#
# They are used to generate Serverless Components.


class HttpEndpoint(l.Infrastructure):
    def __init__(self, name, method, path):
        super().__init__(name)
        self.method = method
        self.path = path


class ObjectStore(l.Infrastructure):
    def __init__(self, name):
        super().__init__(name)


class KVStore(l.Infrastructure):
    def __init__(self, name):
        super().__init__(name)


################################################################################
## Low level infrastructure...


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


class Function(ServerlessComponent):
    def __init__(
        self,
        name: str,
        code: str,
        handler: str,
        memory=128,
        timeout=10,
        runtime="python3.8",
        region="eu-west-2",
    ):
        inputs = dict(
            # --
            code=code,
            handler=handler,
            memory=memory,
            timeout=timeout,
            runtime=runtime,
            region=region,
        )
        super().__init__("@serverless/function", name, inputs)


class Api(ServerlessComponent):
    _count = 1

    def __init__(self, region):
        self.region = region
        self.endpoints = []
        name = "Api" + str(Api._count)
        Api._count += 1
        inputs = dict(
            # --
            region=self.region,
            endpoints=self.endpoints,
        )
        super().__init__("@serverless/api", name, inputs)

    def add_endpoint(self, e: HttpEndpoint):
        self.endpoints.append(
            dict(path=e.path, method=e.method, function=f"${{{e.name}}}")
        )
