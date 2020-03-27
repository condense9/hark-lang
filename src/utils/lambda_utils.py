# https://medium.com/uk-hydrographic-office/developing-and-testing-lambdas-with-pytest-and-localstack-21a111b7f6e8
import json
import os
import os.path
from os.path import join
from zipfile import ZipFile
import tempfile

import boto3
import botocore

CONFIG = botocore.config.Config(retries={"max_attempts": 0})
ZIP_DIR = tempfile.mkdtemp()
THIS_DIR = os.path.dirname(__file__)

print("Zip dir: ", ZIP_DIR)


def lambda_zip_path(function_name):
    return join(ZIP_DIR, function_name + ".zip")


def get_lambda_client():
    return boto3.client(
        "lambda",
        aws_access_key_id="",
        aws_secret_access_key="",
        region_name="eu-west-2",
        endpoint_url="http://localhost:4574",
        config=CONFIG,
    )


def create_lambda_zip(lambda_dir):
    with ZipFile(lambda_zip_path(os.path.basename(lambda_dir)), "w") as z:
        if not os.path.exists(lambda_dir):
            raise Exception(f"No lambda directory: {lambda_dir}")
        for root, dirs, files in os.walk(lambda_dir):
            for f in files:
                # Remove the directory prefix:
                name = join(root, f)
                arcname = name[len(lambda_dir) :]
                z.write(name, arcname=arcname)


def create_lambda(lambda_dir):
    lambda_client = get_lambda_client()
    create_lambda_zip(lambda_dir)
    function_name = os.path.basename(lambda_dir)
    with open(lambda_zip_path(function_name), "rb") as f:
        zipped_code = f.read()
    delete_lambda(function_name)
    lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role="role",
        Handler="main.handler",
        Code=dict(ZipFile=zipped_code),
    )


def delete_lambda(function_name):
    lambda_client = get_lambda_client()
    try:
        lambda_client.delete_function(FunctionName=function_name)
        os.remove(lambda_zip_path(function_name))
    except (FileNotFoundError, lambda_client.exceptions.ResourceNotFoundException):
        pass


def invoke(function_name):
    lambda_client = get_lambda_client()
    response = lambda_client.invoke(
        FunctionName=function_name, InvocationType="RequestResponse"
    )
    return json.loads(response["Payload"].read().decode("utf-8"))
