"""A Terraform synthesiser"""

import json
import os
from os.path import dirname, join
import warnings
from functools import partial
from typing import List, Dict

from .. import infrastructure as inf
from .synthesiser import (
    Synthesiser,
    SynthesisException,
    TextSynth,
    FileSynth,
    bijective_map,
    get_region,
    one_to_many,
    surjective_map,
)
from .synthstate import SynthState
from ..constants import (
    C9_DDB_TABLE_NAME,
    LAMBDA_DIRNAME,
    OUTPUTS_FILENAME,
    HANDLE_NEW,
    HANDLE_EXISTING,
    FN_HANDLE_NEW,
    FN_HANDLE_EXISTING,
)

TF_FILE = "main.tf.json"
LAMBDA_ZIP = "lambda.zip"

NORMAL_INFRA_DIR = "tf_infra"
FUNCTIONS_DIR = "tf_functions"

TF_OUTPUTS_FILENAME = "tf_outputs.json"
GET_OUTPUTS_SCRIPT = "get_outputs.sh"


class TfBlock(TextSynth):
    """Generate a block of terraform JSON"""

    names = []

    def __init__(self, name, params: list, inputs: dict, subdir: str):
        if name in TfBlock.names:
            raise ValueError(f"TF block name '{name}' already used")
        TfBlock.names.append(name)
        self.name = name
        self.params = params

        # credit: https://stackoverflow.com/questions/40401886/how-to-create-a-nested-dictionary-from-a-list-in-python/40402031
        tree_dict = inputs
        for key in reversed(params):
            tree_dict = {key: tree_dict}

        # Terraform can be written in JSON :)
        # https://www.terraform.io/docs/configuration/syntax-json.html
        text = json.dumps(tree_dict, indent=2)
        filename = f"{subdir}/{name}.tf.json"

        super().__init__(filename, text)

    def __repr__(self):
        params = " ".join(self.params)
        return f"<Terraform {params}>"


class TfModule(TfBlock):
    def __init__(self, name, inputs, subdir=NORMAL_INFRA_DIR):
        super().__init__(name, ["module", name], inputs, subdir)


class TfOutput(TfBlock):
    def __init__(self, infra_name, prop_name, value, subdir=NORMAL_INFRA_DIR):
        output_name = _get_output_name(infra_name, prop_name)
        super().__init__(
            f"output_{output_name}", ["output", output_name], dict(value=value), subdir,
        )


class TfResource(TfBlock):
    def __init__(self, kind, name, inputs, subdir=NORMAL_INFRA_DIR):
        super().__init__(f"{kind}_{name}", ["resource", kind, name], inputs, subdir)


class TfOutputs(TfBlock):
    """Create a TF outputs block.

    This will create the Terraform Output. Use in conjunction with GetC9Output
    to create outputs suitable for C9 usage.

    """

    def __init__(self, infra_name, value, subdir=NORMAL_INFRA_DIR):
        super().__init__(
            f"outputs_{infra_name}", ["output", infra_name], dict(value=value), subdir,
        )


class GetC9Output(TextSynth):
    """Add infrastructure outputs to the GET_OUTPUTS_SCRIPT.

    Extract outputs for infrastructure from the TF outputs file and print it as
    a name-value json object.

    """

    def __init__(self, infra_name):
        # https://programminghistorian.org/en/lessons/json-and-jq
        jq_script = f".{infra_name} | {{{infra_name}: .value}}"
        text = f"jq -r '{jq_script}' {TF_OUTPUTS_FILENAME}"
        super().__init__(GET_OUTPUTS_SCRIPT, text)


################################################################################


def make_function(state, res, layers=False):
    name = res.infra_name
    fn = res.infra_spec
    return [
        TfModule(
            name,
            dict(
                source="../tf_modules/c9_lambda",
                function_name=fn.name,
                filename=LAMBDA_ZIP,
                handler=HANDLE_NEW,
                memory_size=fn.memory,
                timeout=fn.timeout,
                runtime="python3.8",
                environment={
                    "variables": dict(C9_HANDLER=fn.name, C9_TIMEOUT=fn.timeout)
                },
            ),
            subdir=FUNCTIONS_DIR,
        ),
        TfOutputs(name, {"this": f"${{module.{name}}}"}, subdir=FUNCTIONS_DIR,),
    ]


def make_bucket(state, res):
    name = res.infra_name
    store = res.infra_spec
    # https://registry.terraform.io/modules/terraform-aws-modules/s3-bucket/aws/1.6.0
    return [
        TfModule(
            name,
            dict(
                source="terraform-aws-modules/s3-bucket/aws",
                version="1.6.0",
                bucket=store.name,
                acl=store.acl,
            ),
        ),
        TfOutputs(
            name,
            {
                # --
                "id": f"${{module.{name}.this_s3_bucket_id}}",
                "arn": f"${{module.{name}.this_s3_bucket_arn}}",
                "region": f"${{module.{name}.this_s3_bucket_region}}",
            },
        ),
        GetC9Output(name),
    ]


def make_dynamodb(state, res):
    name = res.infra_name
    kvstore = res.infra_spec
    # https://registry.terraform.io/modules/terraform-aws-modules/dynamodb-table/aws/0.4.0
    # TODO range_key
    return [
        TfModule(
            name,
            dict(
                source="terraform-aws-modules/dynamodb-table/aws",
                version="0.4.0",
                name=kvstore.name,
                hash_key=next(k for k, v in kvstore.keys.items() if v == "HASH"),
                attributes=[dict(name=k, type=v) for k, v in kvstore.attrs.items()],
            ),
        ),
        TfOutputs(
            name,
            {
                "id": f"${{module.{name}.this_dynamodb_table_id}}",
                "arn": f"${{module.{name}.this_dynamodb_table_arn}}",
            },
        ),
        GetC9Output(name),
    ]


functions = partial(one_to_many, inf.Function, make_function)
buckets = partial(one_to_many, inf.ObjectStore, make_bucket)
dynamodbs = partial(one_to_many, inf.KVStore, make_dynamodb)

# API need to know the function invoke ARN so must go in FUNCTIONS_DIR
# api = partial(surjective_map, inf.HttpEndpoint, make_api) # TODO


def provider_aws(state):
    return SynthState(
        state.service_name,
        state.resources,
        state.iac
        + [
            TfBlock(
                "provider",
                ["provider", "aws"],
                dict(region=get_region()),
                NORMAL_INFRA_DIR,
            )
        ],
        state.deploy_commands,
    )


def provider_localstack(state):
    return SynthState(
        state.service_name,
        state.resources,
        state.iac
        + [
            TfBlock(
                "provider",
                ["provider", "aws"],
                dict(
                    region=get_region(),
                    access_key="foo",
                    secret_key="",
                    skip_credentials_validation=True,
                    skip_requesting_account_id=True,
                    skip_metadata_api_check=True,
                    s3_force_path_style=True,
                    # Endpoints: https://github.com/localstack/localstack#overview
                    # https://www.terraform.io/docs/providers/aws/guides/custom-service-endpoints.html
                    endpoints={
                        "s3": "http://localhost:4566",
                        "dynamodb": "http://localhost:4566",
                        "lambda": "http://localhost:4566",
                        "iam": "http://localhost:4566",
                        "cloudwatchlogs": "http://localhost:4566",
                        "apigateway": "http://localhost:4566",
                    },
                ),
                NORMAL_INFRA_DIR,
            )
        ],
        state.deploy_commands,
    )


def c9_layer(state):
    # https://medium.com/@adhorn/getting-started-with-aws-lambda-layers-for-python-6e10b1f9a5d
    # But not supported on localstack :(
    name = "c9_runtime"
    iac = state.iac + [
        TfResource(
            "aws_lambda_layer_version",
            name,
            dict(
                filename=C9_LAYER_ZIP,
                layer_name=name,
                compatible_runtimes=["python3.8"],
            ),
            subdir=FUNCTIONS_DIR,
        )
    ]
    return SynthState(state.service_name, state.resources, iac, state.deploy_commands)


def roles(state):
    policy = TfModule("c9_policy", dict(source="../tf_modules/c9_policy"))
    attachments = [
        TfResource(
            "aws_iam_role_policy_attachment",
            "policy_{fn.infra_name}",
            {
                # --
                "role": f"${{module.{fn.infra_name}.arn}}",
                "policy_arn": f"${{module.c9_policy.arn}}",
            },
        )
        for fn in state.filter_resources(inf.Function)
    ]
    iac = state.iac + [policy] + attachments
    return SynthState(state.service_name, state.resources, iac, state.deploy_commands)


def _add_c9_infra(state):
    """Add the C9 bits to state"""
    if FN_HANDLE_EXISTING in [i.name for i in state.iac]:
        return state

    c9_handler_existing = TfModule(
        FN_HANDLE_EXISTING,
        dict(
            source="../tf_modules/c9_lambda",
            filename=LAMBDA_ZIP,
            function_name=FN_HANDLE_EXISTING,
            handler=HANDLE_EXISTING,
            runtime="python3.8",
            memory_size=128,
            timeout=300,
        ),
        subdir=FUNCTIONS_DIR,
    )

    table = TfModule(
        "c9_sessions_table",
        dict(
            source="terraform-aws-modules/dynamodb-table/aws",
            version="0.4.0",
            name=C9_DDB_TABLE_NAME,
            hash_key="session_id",
            attributes=[dict(name="session_id", type="S")],
        ),
        subdir=NORMAL_INFRA_DIR,
    )

    iac = state.iac + [c9_handler_existing, table]
    return SynthState(state.service_name, state.resources, iac, state.deploy_commands)


def finalise(state):
    state = _add_c9_infra(state)
    resources = []  # TODO check it's actually taken them all
    modules = FileSynth(join(dirname(__file__), "tf_modules"))
    iac = [modules] + state.iac
    return SynthState(state.service_name, resources, iac, DEPLOY_SCRIPT.split("\n"))


DEPLOY_SCRIPT = f"""
pushd {NORMAL_INFRA_DIR}
    terraform init
    terraform apply
    terraform output -json > ../{TF_OUTPUTS_FILENAME}
popd

bash ./{GET_OUTPUTS_SCRIPT} | jq -s 'add' > {LAMBDA_DIRNAME}/{OUTPUTS_FILENAME}
mv {TF_OUTPUTS_FILENAME} {LAMBDA_DIRNAME}

pushd {LAMBDA_DIRNAME}
    zip -r -q ../{FUNCTIONS_DIR}/{LAMBDA_ZIP} . -x "*__pycache__*"
popd

cp {NORMAL_INFRA_DIR}/provider.tf.json {FUNCTIONS_DIR}

pushd {FUNCTIONS_DIR}
    terraform init
    terraform apply
    terraform output -json > {TF_OUTPUTS_FILENAME}
popd
"""
