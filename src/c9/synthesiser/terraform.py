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
    many_to_many,
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
    LIB_PATH,
)
from .api_spec import get_api_spec

LAMBDA_ZIP = "c9_handler.zip"
LAYER_ZIP = "c9_layer.zip"

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
        self.params = params
        self.inputs = inputs

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
        self.module_name = name
        super().__init__(name, ["module", name], inputs, subdir)


class TfOutput(TfBlock):
    def __init__(self, infra_name, prop_name, value, subdir=NORMAL_INFRA_DIR):
        output_name = _get_output_name(infra_name, prop_name)
        super().__init__(
            f"output_{output_name}", ["output", output_name], dict(value=value), subdir,
        )


class TfResource(TfBlock):
    def __init__(self, kind, name, inputs, subdir=NORMAL_INFRA_DIR):
        self.kind = kind
        self.resource_name = name
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


def _get_layer_name(state):
    return f"c9_{state.service_name}"


def _maybe_get_c9_layer(state) -> list:
    """Get a reference to the c9 layer if it exists"""
    layer_name = _get_layer_name(state)
    existing_layers = [
        i.inputs["layer_name"]
        for i in state.iac
        if isinstance(i, TfResource) and i.kind == "aws_lambda_layer_version"
    ]
    if layer_name in existing_layers:
        return [f"${{aws_lambda_layer_version.{layer_name}.arn}}"]
    else:
        return []


def make_function(state, res):
    name = res.infra_name
    fn = res.infra_spec

    # Use the layer if it exists
    c9_layer = _maybe_get_c9_layer(state)

    return [
        TfModule(
            name,
            dict(
                layers=c9_layer,
                source="../tf_modules/c9_lambda",
                function_name=fn.name,
                filename=LAMBDA_ZIP,
                source_code_hash=f'${{filebase64sha256("{LAMBDA_ZIP}")}}',
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


def make_api(state, endpoints: List[inf.HttpEndpoint]) -> list:
    # API need to know the function invoke ARN so must go in FUNCTIONS_DIR
    lambdas = [e.infra_spec.handler for e in endpoints]
    c9_api_module = "../tf_modules/c9_api"

    for i in state.iac:
        if isinstance(i, TfModule) and i.inputs["source"] == c9_api_module:
            raise SynthesisException("Got more than one API!")

    # https://www.1strategy.com/blog/2017/06/06/how-to-use-amazon-api-gateway-proxy/
    # Ok, HttpEndpoint now means a REST resource.
    #  gateway: api*
    #    api: resource*, deployment*
    #      deployment: uhh
    #      resource: name (e.g. 'todos'), *method
    #        method: http-verb, handler
    #
    # We'll have one API. Multiple resouces, given by the "path" in
    # HttpEndpoint. Each resource has one or more method.

    api_name = f"c9_api_{state.service_name}"
    api_hash = "foo"  # TODO
    api = TfResource(
        "aws_api_gateway_rest_api", api_name, dict(name=api_name), subdir=FUNCTIONS_DIR,
    )

    deployment_name = f"deployment_{api_name}"

    resource_name = lambda path: f"resource_{path}".replace("/", "_")
    resource_paths = list(set([e.infra_spec.path for e in endpoints]))
    resources = [
        TfResource(
            "aws_api_gateway_resource",
            resource_name(path),
            dict(
                rest_api_id=f"${{aws_api_gateway_rest_api.{api_name}.id}}",
                parent_id=f"${{aws_api_gateway_rest_api.{api_name}.root_resource_id}}",
                path_part=path,
            ),
            subdir=FUNCTIONS_DIR,
        )
        for path in resource_paths
    ]

    methods = [
        TfModule(
            e.infra_name,
            dict(
                source="../tf_modules/c9_method",
                method=e.infra_spec.method,
                path=e.infra_spec.path,
                handler=e.infra_spec.handler,
                rest_api_id=f"${{aws_api_gateway_rest_api.{api_name}.id}}",
                resource_id=f"${{aws_api_gateway_resource.{resource_name(e.infra_spec.path)}.id}}",
            ),
            subdir=FUNCTIONS_DIR,
        )
        for e in endpoints
    ]

    deployment = TfResource(
        "aws_api_gateway_deployment",
        deployment_name,
        dict(
            rest_api_id=f"${{aws_api_gateway_rest_api.{api_name}.id}}",
            stage_name="latest",
            description=f"C9 API {api_name} - {api_hash}",
            # Prevent race-conditions
            # https://www.terraform.io/docs/providers/aws/r/api_gateway_deployment.html
            depends_on=[f"module.{m.module_name}" for m in methods],
        ),
        subdir=FUNCTIONS_DIR,
    )
    deployment_output = TfOutputs(
        deployment_name,
        dict(
            deployment=f"${{aws_api_gateway_deployment.{deployment_name}.invoke_url}}"
        ),
        subdir=FUNCTIONS_DIR,
    )

    return [api, deployment, deployment_output] + resources + methods


# def make_bucket_trigger(state, ...) -> list:
#     # https://www.terraform.io/docs/providers/aws/r/s3_bucket_notification.html
#     return TfResource

# bucket_trigger = partial(one_to_many, inf.BucketTrigger, make_bucket_trigger)


functions = partial(one_to_many, inf.Function, make_function)
buckets = partial(one_to_many, inf.ObjectStore, make_bucket)
dynamodbs = partial(one_to_many, inf.KVStore, make_dynamodb)
api = partial(many_to_many, inf.HttpEndpoint, make_api)


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
        state.deploy_commands
        + [f"cp {NORMAL_INFRA_DIR}/provider.tf.json {FUNCTIONS_DIR}"],
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
        state.deploy_commands
        + [f"cp {NORMAL_INFRA_DIR}/provider.tf.json {FUNCTIONS_DIR}"],
    )


def c9_layer(state):
    # https://medium.com/@adhorn/getting-started-with-aws-lambda-layers-for-python-6e10b1f9a5d
    # But not supported on localstack :(
    name = _get_layer_name(state)
    iac = state.iac + [
        TfResource(
            "aws_lambda_layer_version",
            name,
            dict(
                source_code_hash=f'${{filebase64sha256("{LAYER_ZIP}")}}',
                filename=LAYER_ZIP,
                layer_name=name,
                compatible_runtimes=["python3.8"],
            ),
            subdir=FUNCTIONS_DIR,
        )
    ]
    deploy_commands = state.deploy_commands + [
        f"mv {LAMBDA_DIRNAME}/{LIB_PATH} python",
        f'zip -r -g -q {FUNCTIONS_DIR}/{LAYER_ZIP} python -x "*__pycache__*"',
    ]
    return SynthState(state.service_name, state.resources, iac, deploy_commands)


def roles(state):
    policy_name = "c9_policy"
    policy = TfModule(
        policy_name, dict(source="../tf_modules/c9_policy"), subdir=FUNCTIONS_DIR
    )
    attachments = [
        TfResource(
            "aws_iam_role_policy_attachment",
            f"policy_{fn.infra_name}",
            {
                # --
                "role": f"${{module.{fn.infra_name}.role_name}}",
                "policy_arn": f"${{module.{policy_name}.arn}}",
            },
            subdir=FUNCTIONS_DIR,
        )
        for fn in state.filter_resources(inf.Function)
    ]
    iac = state.iac + [policy] + attachments
    return SynthState(state.service_name, state.resources, iac, state.deploy_commands)


def _add_c9_infra(state):
    """Add the C9 bits to state"""
    c9_layer = _maybe_get_c9_layer(state)
    c9_handler_existing = TfModule(
        FN_HANDLE_EXISTING,
        dict(
            source="../tf_modules/c9_lambda",
            source_code_hash=f'${{filebase64sha256("{LAMBDA_ZIP}")}}',
            layers=c9_layer,
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
    iac = state.iac + [modules]
    deploy_commands = state.deploy_commands + DEPLOY_SCRIPT.split("\n")
    return SynthState(state.service_name, resources, iac, deploy_commands)


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

pushd {FUNCTIONS_DIR}
    terraform init
    terraform apply
    terraform output -json > {TF_OUTPUTS_FILENAME}
popd
"""
