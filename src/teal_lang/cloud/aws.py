"""Manage Teal deployment to AWS"""

import json
import os
import os.path
import tempfile
from pathlib import Path
from zipfile import ZipFile

import boto3
import botocore

# https://medium.com/uk-hydrographic-office/developing-and-testing-lambdas-with-pytest-and-localstack-21a111b7f6e8

THIS_DIR = Path(__file__).parent


def lambda_zip_path(zip_dir: Path, function_name):
    return zip_dir / function_name + ".zip"


def get_lambda_client(region: str=None):
    """Get a boto3 Lambda client"""
    endpoint_url = os.environ.get("AWS_ENDPOINT", None)
    return boto3.client(
        "lambda",
        region_name=region,  # Uses AWS_DEFAULT_REGION if None
        endpoint_url=endpoint_url,
        config=botocore.config.Config(retries={"max_attempts": 0}),
    )


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


def delete_lambda(function_name):
    lambda_client = get_lambda_client()
    try:
        lambda_client.delete_function(FunctionName=function_name)
        os.remove(lambda_zip_path(function_name))
    except (FileNotFoundError, lambda_client.exceptions.ResourceNotFoundException):
        pass


def lambda_exists(function_name) -> bool:
    client = get_lambda_client()
    try:
        client.get_function(FunctionName=function_name)
        return True
    except client.exceptions.ResourceNotFoundException:
        return False


def invoke(function_name):
    lambda_client = get_lambda_client()
    response = lambda_client.invoke(
        FunctionName=function_name, InvocationType="RequestResponse"
    )
    return json.loads(response["Payload"].read().decode("utf-8"))


def deploy(config):
    print("Config:")
    print(config)
    print()
    raise NotImplementedError