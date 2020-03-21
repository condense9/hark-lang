"""Infrastructure

The output of synthesiser.py

Actually generate infrastructure.

Infrastructure doesn't reference functions; functions reference infrastructure
(by composition).

"""
import yaml
from dataclasses import dataclass as dc


class Infrastructure:
    region: str


class Component(Infrastructure):
    input_spec = {}
    component_type = None

    def __init__(self, name, **inputs):
        assert self.component_type
        self.name = name
        # self.check_inputs(inputs)
        self.inputs = inputs

    def synthesise(self):
        return serverless_component_yaml(self.name, self.component_type, self.inputs)


# FIXME the input_spec thing isn't nice. Try to use a normal Python function
# interface.
class Function(Component):
    component_type = "@serverless/function"
    input_spec = dict(
        code=str,
        handler=str,
        # ...
    )


class Api(Component):
    component_type = "@serverless/api"
    inputs = dict(code=str,)


def serverless_component_yaml(name, component, inputs):
    """Create YAML for a Serverless Component"""
    return yaml.dump({name: {"component": component, "inputs": inputs}})
