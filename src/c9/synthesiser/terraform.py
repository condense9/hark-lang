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
    one_to_many,
)
from .synthstate import SynthState

TF_FILE = "main.tf.json"
LAMBDA_ZIP = "lambda.zip"

NORMAL_INFRA_DIR = "tf_infra"
FUNCTIONS_DIR = "tf_functions"


class TfBlock(Synthesiser):
    """Generate a block of terraform JSON"""

    names = []

    def __init__(self, name, params: list, inputs: dict, subdir=NORMAL_INFRA_DIR):
        if name in TfBlock.names:
            raise ValueError(f"TF block name '{name}' already used")
        TfBlock.names.append(name)
        self.name = name
        self.params = params
        self.inputs = inputs
        self.filename = f"{subdir}/{name}.tf.json"

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
    def __init__(self, name, inputs, subdir=NORMAL_INFRA_DIR):
        super().__init__(name, ["module", name], inputs, subdir)


class TfOutput(TfBlock):
    def __init__(self, block_name, name, value):
        super().__init__(block_name + "_outputs", ["output", name], dict(value=value))


################################################################################


def make_function(state, fn):
    return TfModule(
        "lambda_" + fn.name,
        dict(
            source="spring-media/lambda/aws",
            version="5.0.0",
            filename=LAMBDA_ZIP,
            function_name=fn.name,
            handler="main.event_handler",  # TODO make this not hardcoded
            runtime=fn.runtime,
            environment={"variables": dict(C9_HANDLER=fn.name, C9_TIMEOUT=fn.timeout)},
        ),
        subdir=FUNCTIONS_DIR,
    )


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
    # https://registry.terraform.io/modules/terraform-aws-modules/dynamodb-table/aws/0.4.0
    # TODO range_key
    mod_name = "ddb_" + kvstore.name
    return [
        TfModule(
            mod_name,
            dict(
                source="terraform-aws-modules/dynamodb-table/aws",
                version="0.4.0",
                name=kvstore.name,
                hash_key=next(k for k, v in kvstore.keys.items() if v == "HASH"),
                attributes=[dict(name=k, type=v) for k, v in kvstore.attrs.items()],
            ),
        ),
        TfOutput(mod_name, "arn", f"${{module.{mod_name}.this_dynamodb_table_arn}}"),
    ]


functions = partial(bijective_map, inf.Function, make_function)
buckets = partial(bijective_map, inf.ObjectStore, make_bucket)
dynamodbs = partial(one_to_many, inf.KVStore, make_dynamodb)
# api = partial(surjective_map, inf.HttpEndpoint, make_api) # TODO


def finalise(state):
    resources = []  # TODO check it's actually taken them all

    frontmatter = TfBlock("provider", ["provider", "aws"], dict(region=get_region()))

    c9_handler = TfModule(
        "lambda_c9_handler",
        dict(
            source="spring-media/lambda/aws",
            version="5.0.0",
            filename=LAMBDA_ZIP,
            function_name="c9_handler",
            handler="main.c9_handler",
            runtime="python3.8",
        ),
        subdir=FUNCTIONS_DIR,
    )

    iac = [frontmatter, c9_handler] + state.iac

    deploy_commands = f"""
        pushd {NORMAL_INFRA_DIR}
        terraform init
        terraform apply
        terraform output -json > ../{state.code_dir}/output.json
        popd
        pushd {state.code_dir}
        zip -r ../{FUNCTIONS_DIR}/{LAMBDA_ZIP} . -x "*__pycache__*"
        popd
        cp {NORMAL_INFRA_DIR}/provider.tf.json {FUNCTIONS_DIR}
        pushd {FUNCTIONS_DIR}
        terraform init
        terraform apply
        popd
    """.split(
        "\n"
    )

    return SynthState(
        state.service_name, resources, iac, deploy_commands, state.code_dir
    )
