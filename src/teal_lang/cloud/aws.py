"""Manage Teal deployments in AWS"""

import json
import logging
import os
import os.path
import random
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


class TealFunction:
    @staticmethod
    def create_or_update(config):
        pass


class FnSetexe(TealFunction):
    name = "set_exe"
    handler = "teal_lang.executors.awslambda.set_exe"


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
    # FnSetexe,
    # FnNew,
    # FnResume,
    # FnGetoutput,
    # FnGetEvents,
    # FnVersion,
    # DataTable,
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
        LOG.info(f"Success: {res.__name__} {res.resource_name(config)}")


def destroy(config):
    """Destroy infrastructure created for this config"""
    setup_region(config)
    setup_deployment_id(config)

    if not config.service.deployment_id:
        raise DeploymentFailed("No Deployment ID - can't destroy anything")

    LOG.info(f"Destroying: {config.service.deployment_id}")

    for res in CORE_RESOURCES:
        res.delete_if_exists()
