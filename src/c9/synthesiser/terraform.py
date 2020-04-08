"""A Terraform synthesiser"""

import json
import os
import warnings
from functools import partial
from typing import List

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

TF_FILE = "main.tf.json"
LAMBDA_ZIP = "lambda.zip"


class TfBlock(Synthesiser):
    """Generate a block of terraform JSON"""

    names = []

    def __init__(self, name, params: list, inputs: dict):
        if name in TfBlock.names:
            raise ValueError(f"TF block name '{name}' already used")
        TfBlock.names.append(name)
        self.name = name
        self.params = params
        self.inputs = inputs
        self.filename = f"{name}.tf.json"

    def generate(self):
        # credit: https://stackoverflow.com/questions/40401886/how-to-create-a-nested-dictionary-from-a-list-in-python/40402031
        tree_dict = self.inputs
        for key in reversed(self.params):
            tree_dict = {key: tree_dict}
        return json.dumps(tree_dict, indent=2)

    def __repr__(self):
        params = " ".join(self.params)
        return f"<Terraform {params}>"


class TfModule(TfBlock):
    def __init__(self, name, inputs):
        super().__init__(name, ["module", name], inputs)


def make_function(state, fn):
    return TfModule(
        "lambda_" + fn.name,
        dict(
            source="spring-media/lambda/aws",
            version="5.0.0",
            filename=LAMBDA_ZIP,
            function_name=fn.name,
            handler="main.event_handler",
            runtime=fn.runtime,
            environment={"variables": dict(C9_HANDLER=fn.name, C9_TIMEOUT=fn.timeout)},
        ),
    )


# module "s3-bucket" {
#   source  = "terraform-aws-modules/s3-bucket/aws"
#   version = "1.6.0"
#   # insert the 6 required variables here
# }


def make_bucket(state, store):
    return TfModule(
        "s3_" + store.name,
        dict(
            source="terraform-aws-modules/s3-bucket/aws",
            version="1.6.0",
            bucket=store.name,
            acl=store.acl,
        ),
    )


def make_dynamodb(state, kvstore):
    # TODO range_key
    return TfModule(
        "ddb_" + kvstore.name,
        dict(
            source="terraform-aws-modules/dynamodb-table/aws",
            version="0.4.0",
            name=kvstore.name,
            hash_key=next(k for k, v in kvstore.keys.items() if v == "HASH"),
            attributes=[dict(name=k, type=v) for k, v in kvstore.attrs.items()],
        ),
    )


functions = partial(bijective_map, inf.Function, make_function)
buckets = partial(bijective_map, inf.ObjectStore, make_bucket)
dynamodbs = partial(bijective_map, inf.KVStore, make_dynamodb)
# api = partial(surjective_map, inf.HttpEndpoint, make_api)


def finalise(state):
    # resources = state.resources
    resources = []
    frontmatter = TfBlock("provider", ["provider", "aws"], dict(region=get_region()))
    iac = [frontmatter] + state.iac
    deploy_commands = [
        f"pushd {state.code_dir}/",
        f'zip -r ../{LAMBDA_ZIP} . -x "*__pycache__*"',
        "popd",
        "terraform init",
        "terraform apply",
    ]
    return SynthState(
        state.service_name, resources, iac, deploy_commands, state.code_dir
    )
