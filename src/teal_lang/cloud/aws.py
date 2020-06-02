"""Manage Teal deployments in AWS"""

import json
import logging
import os
import os.path
import random
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Tuple
from zipfile import ZipFile

import boto3
import botocore
from botocore.client import ClientError

from .. import config as teal_config

LOG = logging.getLogger(__name__)


# https://medium.com/uk-hydrographic-office/developing-and-testing-lambdas-with-pytest-and-localstack-21a111b7f6e8

THIS_DIR = Path(__file__).parent


def lambda_zip_path(zip_dir: Path, function_name):
    return zip_dir / function_name + ".zip"


def create_lambda_zip(lambda_dir: str, lib_dir: str = None) -> str:
    zip_name = lambda_zip_path(basename(lambda_dir))
    with ZipFile(zip_name, "w") as z:
        if not os.path.exists(lambda_dir):
            raise Exception(f"No lambda directory: {lambda_dir}")
        for root, dirs, files in os.walk(lambda_dir):
            for f in files:
                # Remove the directory prefix:
                name = join(root, f)
                arcname = name[len(lambda_dir) :]
                z.write(name, arcname=arcname)
        if lib_dir:
            # NOTE - will overwrite lib_dir_name/ in the archive
            for root, dirs, files in os.walk(lib_dir):
                for f in files:
                    name = join(root, f)
                    lib_dir_name = basename(lib_dir)
                    arcname = name[len(lib_dir) - len(lib_dir_name) :]
                    z.write(name, arcname=arcname)
    return zip_name


def create_lambda(lambda_dir, lib_dir=None):
    create_lambda_zip(lambda_dir, lib_dir)
    function_name = basename(lambda_dir)
    delete_lambda(function_name)
    lambda_from_zip(function_name, lambda_zip_path(function_name))


def lambda_from_zip(
    function_name, zipfile, handler="main.handler", env=None, timeout=3
):
    with open(zipfile, "rb") as f:
        zipped_code = f.read()
    if not env:
        env = {}
    lambda_client = get_lambda_client()
    lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role="role",
        Handler=handler,
        Code=dict(ZipFile=zipped_code),
        Timeout=timeout,
        Environment=dict(Variables=env),
    )


def delete_lambda(function_name: str):
    """Delete a Lambda function if it exists"""
    lambda_client = get_lambda_client()
    try:
        lambda_client.delete_function(FunctionName=function_name)
    except lambda_client.exceptions.ResourceNotFoundException:
        pass


def lambda_exists(function_name: str) -> bool:
    """Check if a function exists"""
    client = get_lambda_client()
    try:
        client.get_function(FunctionName=function_name)
        return True
    except client.exceptions.ResourceNotFoundException:
        return False


class InvokeError(Exception):
    "Failed to invoke function"


FunctionLogs = str
FunctionResponse = str


def invoke(
    function_name: str, payload: bytes = None
) -> Tuple[FunctionLogs, FunctionResponse]:
    """Invoke a Lambda function"""
    lambda_client = get_lambda_client()
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=payload,
        LogType="Tail",
    )

    if not 200 <= response["StatusCode"] < 300:
        raise InvokeError(response)

    logs = response["LogResult"]
    payload = response["Payload"].read().decode("utf-8")

    return logs, payload


class DeploymentFailed(Exception):
    """Failed to deploy"""


def get_client(config, service):
    """Get a boto3 client for SERVICE, setting endpoint and region"""
    args = {}

    endpoint_url = os.environ.get("AWS_ENDPOINT", None)
    if endpoint_url:
        args["endpoint_url"] = endpoint_url

    return boto3.client(
        service,
        region_name=config.service.region,
        config=botocore.config.Config(retries={"max_attempts": 0}),
        **args,
    )


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
class DataBucket:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}-{config.service.name}"

    @staticmethod
    def exists(config):
        client = get_client(config, "s3")
        name = DataBucket.resource_name(config)
        try:
            client.head_bucket(Bucket=name)
            return True
        except ClientError:
            return False

    @staticmethod
    def create(config):
        name = DataBucket.resource_name(config)
        client = get_client(config, "s3")

        # Example: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-creating-buckets.html
        try:
            location = {"LocationConstraint": config.service.region}
            client.create_bucket(
                Bucket=name, ACL="private", CreateBucketConfiguration=location
            )
        except ClientError as exc:
            raise DeploymentFailed from exc

    @staticmethod
    def create_or_update(config):
        """Create the data bucket if it doesn't exist"""
        name = DataBucket.resource_name(config)
        client = get_client(config, "s3")
        if not DataBucket.exists(config):
            DataBucket.create(config)

    @staticmethod
    def delete_if_exists(config):
        raise NotImplementedError


def get_data_dir(config) -> Path:
    """Get path to the Teal data directory, ensuring it exists"""
    data_dir = Path(config.service.data_dir)

    if not data_dir.is_absolute():
        data_dir = (Path(config.root) / config.service.data_dir).resolve()

    if not data_dir.is_dir():
        os.makedirs(str(data_dir))

    return data_dir


def upload_if_necessary(client, bucket, key, filename):
    """Upload a file if it doesn't already exist"""
    # TODO check MD5 first
    try:
        response = client.upload_file(filename, bucket, key)
    except ClientError as exc:
        raise DeploymentFailed from exc


class S3File:
    """A file in S3. This class must be subclassed"""

    @classmethod
    def resource_name(cls, config) -> list:
        # NOTE: no nested folders. Could do later if necessary.
        return cls.key

    @classmethod
    def create_or_update(cls, config):
        """Create the file and upload it"""
        data_dir = get_data_dir(config)
        dest_file = data_dir / cls.key
        cls.get_file(config, dest_file)

        client = get_client(config, "s3")
        bucket = DataBucket.resource_name(config)
        upload_if_necessary(client, bucket, cls.key, str(dest_file))


class TealPackage(S3File):
    key = "teal.zip"

    @staticmethod
    def get_file(config, dest: Path):
        """Create the Teal code Zip, saving it in dest"""
        root = Path(__file__).parents[3]
        script = root / "scripts" / "make_lambda_dist.sh"

        if not dest.exists():
            LOG.info(f"Building Teal Lambda package in {dest}...")
            subprocess.check_output([str(script), str(dest)])


class SourceLayerPackage(S3File):
    key = "layer.zip"

    @staticmethod
    def get_file(config, dest: Path):
        """Create the source code layer Zip, saving it in dest"""
        root = Path(__file__).parents[3]
        script = root / "scripts" / "make_layer.sh"

        LOG.info(f"Building Source Layer package in {dest}...")
        subprocess.check_output([str(script), config.service.python_src, str(dest)])


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#client
class DataTable:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}-{config.service.name}"

    @staticmethod
    def exists(config):
        client = get_client(config, "dynamodb")
        name = DataTable.resource_name(config)
        try:
            client.describe_table(TableName=name)
            return True
        except client.exceptions.ResourceNotFoundException:
            return False

    @staticmethod
    def get_arn(config):
        client = get_client(config, "dynamodb")
        name = DataTable.resource_name(config)
        res = client.describe_table(TableName=name)
        return res["Table"]["TableArn"]

    @staticmethod
    def create_or_update(config):
        client = get_client(config, "dynamodb")
        name = DataTable.resource_name(config)

        if DataTable.exists(config):
            return

        res = client.create_table(
            TableName=name,
            AttributeDefinitions=[
                # --
                dict(AttributeName="session_id", AttributeType="S")
            ],
            KeySchema=[
                # --
                dict(AttributeName="session_id", KeyType="HASH")
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=name)


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#client
class ExecutionRole:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}-{config.service.name}"

    @staticmethod
    def get_arn(config):
        client = get_client(config, "iam")
        res = client.get_role(RoleName=ExecutionRole.resource_name(config))
        return res["Role"]["Arn"]

    @staticmethod
    def exists(config):
        client = get_client(config, "iam")
        try:
            res = client.get_role(RoleName=ExecutionRole.resource_name(config))
            return True
        except client.exceptions.NoSuchEntityException:
            return False

    @staticmethod
    def delete_if_exists(config):
        if not ExecutionRole.exists(config):
            return

        client = get_client(config, "iam")
        name = ExecutionRole.resource_name(config)
        client.delete_role_policy(RoleName=name, PolicyName="default")
        client.delete_role(RoleName=name)

    @staticmethod
    def create_or_update(config):
        if ExecutionRole.exists(config):
            return

        client = get_client(config, "iam")
        name = ExecutionRole.resource_name(config)
        table_arn = DataTable.get_arn(config)

        policy = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    # TODO log streams
                    # {
                    #     "Action": ["logs:CreateLogStream", "logs:CreateLogGroup"],
                    #     "Resource": [
                    #         "arn:aws:logs:eu-west-2:297409317403:log-group:/aws/lambda/tryit-prod*:*"
                    #     ],
                    #     "Effect": "Allow",
                    # },
                    # {
                    #     "Action": ["logs:PutLogEvents"],
                    #     "Resource": [
                    #         "arn:aws:logs:eu-west-2:297409317403:log-group:/aws/lambda/tryit-prod*:*:*"
                    #     ],
                    #     "Effect": "Allow",
                    # },
                    {
                        "Action": [
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:DescribeTable",
                        ],
                        "Resource": table_arn,
                        "Effect": "Allow",
                    },
                    {
                        "Action": ["lambda:InvokeFunction"],
                        "Resource": "*",  # TODO make it only the resume FN?
                        "Effect": "Allow",
                    },
                ],
            }
        )

        assume_role_policy = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        )

        client.create_role(
            RoleName=name, AssumeRolePolicyDocument=assume_role_policy,
        )
        client.put_role_policy(
            RoleName=name, PolicyName="default", PolicyDocument=policy
        )
        client.attach_role_policy(
            RoleName=name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )


class SourceLayer:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}-{config.service.name}-src"

    @staticmethod
    def get_arn(config):
        client = get_client(config, "lambda")
        name = SourceLayer.resource_name(config)
        res = client.list_layer_versions(LayerName=name, MaxItems=1)
        try:
            return res["LayerVersions"][0]["LayerVersionArn"]
        except IndexError:
            return None

    @staticmethod
    def create_or_update(config):
        client = get_client(config, "lambda")
        name = SourceLayer.resource_name(config)
        # TODO - don't publish if it hasn't changed
        client.publish_layer_version(
            LayerName=name,
            Content=dict(
                # --
                S3Bucket=DataBucket.resource_name(config),
                S3Key=SourceLayerPackage.key,
            ),
        )


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#client
class TealFunction:
    needs_src = False

    @classmethod
    def resource_name(cls, config):
        return f"teal-{config.service.deployment_id}-{config.service.name}-{cls.name}"

    @classmethod
    def exists(cls, config):
        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        try:
            res = client.get_function(FunctionName=name)
            return True
        except client.exceptions.ResourceNotFoundException:
            return False

    @classmethod
    def create_or_update(cls, config):
        if cls.exists(config):
            cls.update(config)
        else:
            cls.create(config)

        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        client.publish_version(FunctionName=name)

        waiter = client.get_waiter("function_active")
        waiter.wait(FunctionName=name)

    @classmethod
    def update(cls, config):
        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        client.update_function_code(
            FunctionName=name,
            S3Bucket=DataBucket.resource_name(config),
            S3Key=TealPackage.key,
            Publish=False,
        )
        if cls.needs_src:
            client.update_function_configuration(
                FunctionName=name, Layers=[SourceLayer.get_arn(config)]
            )

    @classmethod
    def create(cls, config):
        client = get_client(config, "lambda")
        role_arn = ExecutionRole.get_arn(config)
        name = cls.resource_name(config)
        layers = [SourceLayer.get_arn(config)] if cls.needs_src else []

        client.create_function(
            FunctionName=name,
            Runtime="python3.8",
            Role=role_arn,
            Handler=cls.handler,
            Publish=False,
            Code=dict(
                # --
                S3Bucket=DataBucket.resource_name(config),
                S3Key=TealPackage.key,
            ),
            Timeout=config.service.lambda_timeout,  # TODO make per-function?
            Layers=layers,
        )


class FnSetexe(TealFunction):
    name = "set_exe"
    handler = "teal_lang.executors.awslambda.set_exe"


class FnNew(TealFunction):
    name = "new"
    handler = "teal_lang.executors.awslambda.new"
    needs_src = True


class FnResume(TealFunction):
    name = "resume"
    handler = "teal_lang.executors.awslambda.resume"
    needs_src = True


class FnGetoutput(TealFunction):
    name = "getoutput"
    handler = "teal_lang.executors.awslambda.getoutput_apigw"


class FnGetEvents(TealFunction):
    name = "getevents"
    handler = "teal_lang.executors.awslambda.getevents_apigw"


class FnVersion(TealFunction):
    name = "version"
    handler = "teal_lang.executors.awslambda.version_apigw"


# ... TODO


def create_deployment_id(config):
    """Make a random deployment ID"""
    # only taking 16 chars to make it more readable
    did = uuid.uuid4().hex[:16]
    LOG.info(f"Using new deployment ID {did}")

    did_file = Path(config.service.deployment_id_file)
    LOG.info(f"Writing deployment ID to {did_file}")

    with open(str(did_file), "w") as f:
        f.write(did)

    config.service.deployment_id = did


def get_deployment_id(config: teal_config.Config) -> str:
    """Try to find a deployment ID"""
    if config.service.deployment_id:
        return config.service.deployment_id

    did_file = Path(config.service.deployment_id_file)
    if did_file.exists():
        with open(str(did_file), "r") as f:
            return f.read().strip()

    return os.environ.get("TEAL_DEPLOYMENT_ID", None)


def setup_deployment_id(config):
    if not config.service.deployment_id:
        config.service.deployment_id = get_deployment_id(config)


def setup_region(config: teal_config.Config):
    """Ensure that config.service.region is set"""
    if not config.service.region:
        session = boto3.session.Session()
        config.service.region = session.region_name
    LOG.info(f"Using region {config.service.region}")


CORE_RESOURCES = [
    DataBucket,
    TealPackage,
    SourceLayerPackage,
    DataTable,
    ExecutionRole,
    SourceLayer,
    FnSetexe,
    FnNew,
    FnResume,
    FnGetoutput,
    FnGetEvents,
    FnVersion,
]


def deploy(config):
    """Deploy (or update) infrastructure for this config"""
    setup_region(config)
    setup_deployment_id(config)

    if not config.service.deployment_id:
        create_deployment_id(config)

    LOG.info(f"Deploying: {config.service.deployment_id}")

    for res in CORE_RESOURCES:
        res.create_or_update(config)
        LOG.info(f"Resource: {res.__name__} {res.resource_name(config)}")


def destroy(config):
    """Destroy infrastructure created for this config"""
    setup_region(config)
    setup_deployment_id(config)

    if not config.service.deployment_id:
        raise DeploymentFailed("No Deployment ID - can't destroy anything")

    LOG.info(f"Destroying: {config.service.deployment_id}")

    # destroy in reverse order so dependencies go first
    for res in reversed(CORE_RESOURCES):
        res.delete_if_exists()
