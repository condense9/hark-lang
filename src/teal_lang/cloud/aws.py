"""Manage Teal deployments in AWS"""

import base64
import json
import logging
import os
import os.path
import random
import shutil
import subprocess
import time
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Tuple, Union
from zipfile import ZipFile

import boto3
import botocore
from botocore.client import ClientError

import deterministic_zip as dz

from .. import config as teal_config

LOG = logging.getLogger(__name__)


# https://medium.com/uk-hydrographic-office/developing-and-testing-lambdas-with-pytest-and-localstack-21a111b7f6e8

THIS_DIR = Path(__file__).parent


class DeploymentFailed(Exception):
    """Failed to deploy"""


class InvokeError(Exception):
    "Failed to invoke function"


@lru_cache
def get_client(config, service):
    """Get a boto3 client for SERVICE, setting endpoint and region"""
    args = {}

    endpoint_url = os.environ.get("AWS_ENDPOINT", None)
    if endpoint_url:
        args["endpoint_url"] = endpoint_url

    return boto3.client(
        service,
        region_name=config.service.region,
        # config=botocore.config.Config(retries={"max_attempts": 0}),
        **args,
    )


def hash_file(filename: Path) -> str:
    """Get the (base64 encoded) SHA256 hash of a file"""
    with open(filename, "rb") as f:
        return base64.b64encode(sha256(f.read()).digest()).decode()


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
class DataBucket:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}"

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
            LOG.info(f"created bucket {name}")
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
    def destroy_if_exists(config):
        name = DataBucket.resource_name(config)
        client = get_client(config, "s3")
        try:
            client.delete_bucket(Bucket=name)
            LOG.info(f"Deleted bucket {name}")
        except client.exceptions.NoSuchBucket:
            pass


def get_data_dir(config) -> Path:
    """Get path to the Teal data directory, ensuring it exists"""
    data_dir = config.service.data_dir

    if not data_dir.is_absolute():
        data_dir = (Path(config.root) / config.service.data_dir).resolve()

    if not data_dir.is_dir():
        os.makedirs(str(data_dir))

    return data_dir


def upload_if_necessary(client, bucket, key, filename):
    """Upload a file if it doesn't already exist"""
    new_hashsum = hash_file(filename)
    hash_key = "sha256"

    # only upload if the object doesn't exist or the hash is different
    try:
        res = client.head_object(Bucket=bucket, Key=key)
        if new_hashsum == res["Metadata"][hash_key]:
            return
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Message"] == "Not Found":
            pass
    except KeyError:
        # also catch KeyError just in case
        pass

    try:
        with open(filename, "rb") as f:
            response = client.put_object(
                Body=f, Bucket=bucket, Key=key, Metadata={hash_key: new_hashsum}
            )
            LOG.info(f"Uploaded {filename}")

    except ClientError as exc:
        raise DeploymentFailed from exc


class S3File:
    """A file in S3. This class must be subclassed"""

    @classmethod
    def resource_name(cls, config) -> list:
        # NOTE: no nested folders. Could do later if necessary.
        return cls.key

    @classmethod
    def local_file(cls, config) -> Path:
        data_dir = get_data_dir(config)
        return data_dir / cls.key

    @classmethod
    def local_sha(cls, config) -> str:
        local_file = cls.local_file(config)
        return hash_file(local_file)

    @classmethod
    def create_or_update(cls, config):
        """Create the file and upload it"""
        dest_file = cls.local_file(config)
        cls.get_file(config, dest_file)

        client = get_client(config, "s3")
        bucket = DataBucket.resource_name(config)
        upload_if_necessary(client, bucket, cls.key, str(dest_file))

    @classmethod
    def destroy_if_exists(cls, config):
        client = get_client(config, "s3")
        bucket = DataBucket.resource_name(config)
        try:
            client.delete_object(Bucket=bucket, Key=cls.key)
            LOG.info(f"Deleted {cls.key} from {bucket}")
        except (client.exceptions.NoSuchKey, client.exceptions.NoSuchBucket):
            pass


class TealPackage(S3File):
    key = "teal.zip"

    @staticmethod
    def get_file(config, dest: Path):
        """Create the Teal code Zip, saving it in dest"""
        LOG.info(f"Copying Teal Lambda package to {dest}")

        # NOTE - magic here. Relies on you running "scripts/make_lambda_dist.sh"
        # before deployment, which creates teal_lambda.zip at the repository
        # root, and is packaged in the teal pip distribution. Not very nice or
        # clean, and we find a better way.
        zipfile = Path(__file__).parents[3] / "teal_lambda.zip"
        shutil.copyfile(zipfile, dest)


def zip_dir(dirname: Path, dest: Path, deterministic=True):
    """Zip a directory"""
    # https://github.com/bboe/deterministic_zip/blob/master/deterministic_zip/__init__.py
    with zipfile.ZipFile(dest, "w") as zip_file:
        dz.add_directory(zip_file, dirname, os.path.basename(dirname))


class SourceLayerPackage(S3File):
    key = "layer.zip"

    @staticmethod
    def get_file(config, dest: Path):
        """Create the source code layer Zip, saving it in dest"""
        root = Path(__file__).parents[3]

        if not config.service.python_src.exists():
            raise DeploymentFailed(
                f"Python source directory ({config.service.python_src}) not found"
            )

        LOG.info(f"Building Source Layer package in {dest}...")
        workdir = get_data_dir(config) / "source_build" / "python"
        os.makedirs(workdir, exist_ok=True)

        # User source
        shutil.copytree(
            config.service.python_src,
            workdir / config.service.python_src.name,
            dirs_exist_ok=True,
        )

        # Pip requirements if they exist
        reqs_file = config.service.python_requirements
        if reqs_file.exists():
            subprocess.check_output(
                ["pip", "install", "-q", "--target", workdir, "-r", reqs_file]
            )

        # Make sure the zip is not empty
        with open(workdir / "packaged_by_teal.txt", "w") as f:
            f.write("Packed by Teal :)")

        zip_dir(workdir, dest)


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#client
class DataTable:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}"

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

        client.create_table(
            TableName=name,
            AttributeDefinitions=[
                # --
                dict(AttributeName="session_id", AttributeType="S"),
                dict(AttributeName="item_id", AttributeType="S"),
            ],
            KeySchema=[
                # --
                dict(AttributeName="session_id", KeyType="HASH"),
                dict(AttributeName="item_id", KeyType="RANGE"),
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=name)
        LOG.info(f"Created Table {name}")

    @staticmethod
    def destroy_if_exists(config):
        client = get_client(config, "dynamodb")
        name = DataTable.resource_name(config)
        try:
            client.delete_table(TableName=name)
            waiter = client.get_waiter("table_not_exists")
            waiter.wait(TableName=name)
            LOG.info(f"Deleted Table {name}")
        except client.exceptions.ResourceNotFoundException:
            pass


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#client
class ExecutionRole:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}"

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
    def destroy_if_exists(config):
        if not ExecutionRole.exists(config):
            return

        client = get_client(config, "iam")
        name = ExecutionRole.resource_name(config)

        try:
            client.delete_role_policy(RoleName=name, PolicyName="default")
        except client.exceptions.NoSuchEntityException:
            pass

        try:
            client.delete_role_policy(RoleName=name, PolicyName="s3_access")
        except client.exceptions.NoSuchEntityException:
            pass

        try:
            client.detach_role_policy(
                RoleName=name,
                PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        except client.exceptions.NoSuchEntityException:
            pass

        client.delete_role(RoleName=name)
        LOG.info(f"Deleted execution role {name}")

    @staticmethod
    def get_s3_access_policy(config) -> dict:
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        f"arn:aws:s3:::{bucket}/*"
                        for bucket in config.service.s3_access
                    ],
                }
            ],
        }

    @staticmethod
    def update_s3_access_policy(config):
        client = get_client(config, "iam")
        name = ExecutionRole.resource_name(config)
        try:
            current = client.get_role_policy(
                RoleName=ExecutionRole.resource_name(config), PolicyName="s3_access"
            )
            current_statement = current["PolicyDocument"]["Statement"]
        except client.exceptions.NoSuchEntityException:
            current = None

        s3_access_policy = ExecutionRole.get_s3_access_policy(config)
        if not current or current_statement != s3_access_policy["Statement"]:
            try:
                client.delete_role_policy(RoleName=name, PolicyName="s3_access")
            except client.exceptions.NoSuchEntityException:
                pass

            client.put_role_policy(
                RoleName=name,
                PolicyName="s3_access",
                PolicyDocument=json.dumps(s3_access_policy),
            )

            LOG.info(f"Updated S3 bucket access for {name}")

    @staticmethod
    def create_or_update(config):
        if ExecutionRole.exists(config):
            ExecutionRole.update_s3_access_policy(config)
            # ExecutionRole.update_trigger_policy(config)
            return

        client = get_client(config, "iam")
        name = ExecutionRole.resource_name(config)
        table_arn = DataTable.get_arn(config)

        policy = {
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

        s3_access_policy = ExecutionRole.get_s3_access_policy(config)

        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        client.create_role(
            RoleName=name, AssumeRolePolicyDocument=json.dumps(assume_role_policy),
        )
        client.put_role_policy(
            RoleName=name, PolicyName="default", PolicyDocument=json.dumps(policy)
        )
        client.put_role_policy(
            RoleName=name,
            PolicyName="s3_access",
            PolicyDocument=json.dumps(s3_access_policy),
        )
        client.attach_role_policy(
            RoleName=name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        # It takes a while for the execution policy to propagate, and the lambda
        # creation fails if it isn't. There isn't a waiter to check that it's
        # propagated :( See also
        # https://github.com/Miserlou/Zappa/commit/fa1b224fc43c7c8739dd179f9a038d31e13911e9
        # Hack for now:
        time.sleep(10)


class SourceLayer:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}-src"

    @staticmethod
    def get_arn(config) -> Union[None, str]:
        """Get ARN and SHA256 of the highest-version layer"""
        client = get_client(config, "lambda")
        name = SourceLayer.resource_name(config)
        res = client.list_layer_versions(LayerName=name, MaxItems=1)
        try:
            return res["LayerVersions"][0]["LayerVersionArn"]
        except IndexError:
            return None

    @staticmethod
    def get_latest_sha256(config) -> Union[None, str]:
        """Get ARN and SHA256 of the highest-version layer"""
        client = get_client(config, "lambda")
        arn = SourceLayer.get_arn(config)
        if arn:
            res = client.get_layer_version_by_arn(Arn=arn)
            return res["Content"]["CodeSha256"]

    @staticmethod
    def create_or_update(config):
        current_sha = SourceLayer.get_latest_sha256(config)
        local_sha = SourceLayerPackage.local_sha(config)

        if current_sha == local_sha:
            return

        LOG.info(f"Layer changed, updating")
        client = get_client(config, "lambda")
        name = SourceLayer.resource_name(config)
        client.publish_layer_version(
            LayerName=name,
            Content=dict(
                # --
                S3Bucket=DataBucket.resource_name(config),
                S3Key=SourceLayerPackage.key,
            ),
        )
        current_sha = SourceLayer.get_latest_sha256(config)
        assert current_sha == local_sha

    @staticmethod
    def destroy_if_exists(config):
        client = get_client(config, "lambda")
        name = SourceLayer.resource_name(config)
        while True:
            versions = client.list_layer_versions(LayerName=name)
            if not versions["LayerVersions"]:
                break
            for v in versions["LayerVersions"]:
                number = v["Version"]
                client.delete_layer_version(LayerName=name, VersionNumber=number)
                LOG.info(f"Deleted layer {name} v{number}")


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#client
class TealFunction:
    needs_src_layer = False

    @classmethod
    def create_extra_permissions(cls, config):
        pass

    @classmethod
    def resource_name(cls, config):
        return f"teal-{config.service.deployment_id}-{cls.name}"

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
    def get_arn(cls, config):
        """Get the ARN. Raises ResourceNotFoundException if it doesn't exist"""
        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        res = client.get_function(FunctionName=name)
        return res["Configuration"]["FunctionArn"]

    @classmethod
    def src_layers_list(cls, config):
        """Create the list of layers to provide user src code"""
        # NOTE: if the "extra" layers come last, you may get error: "Layer
        # conversion failed: Some files need to be overridden by layers but
        # don't have write permissions;". Fixed by putting extra layers first.
        # Don't fully understand it though. See also:
        # https://forums.aws.amazon.com/thread.jspa?messageID=908553
        return list(config.service.extra_layers) + [SourceLayer.get_arn(config)]

    @classmethod
    def create_or_update(cls, config):
        if cls.exists(config):
            needs_publish = cls.update(config)
        else:
            cls.create(config)
            needs_publish = True

        if needs_publish:
            client = get_client(config, "lambda")
            name = cls.resource_name(config)
            client.publish_version(FunctionName=name)

            waiter = client.get_waiter("function_active")
            waiter.wait(FunctionName=name)

    @classmethod
    def update(cls, config) -> bool:
        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        needs_publish = False
        current_config = client.get_function_configuration(FunctionName=name)

        # Check if Teal code needs to be updated
        current_sha = current_config["CodeSha256"]
        required_sha = TealPackage.local_sha(config)

        if current_sha != required_sha:
            LOG.info(f"Code for {name} changed, updating function")
            client.update_function_code(
                FunctionName=name,
                S3Bucket=DataBucket.resource_name(config),
                S3Key=TealPackage.key,
                Publish=False,
            )
            needs_publish = True

        # Check if layers need to be updated
        current_layers = [layer["Arn"] for layer in current_config["Layers"]]
        required_layers = cls.src_layers_list(config)
        env_vars = cls.get_environment_variables(config)

        if (
            current_config["MemorySize"] != config.service.lambda_memory
            or current_config["Timeout"] != config.service.lambda_timeout
            or (cls.needs_src_layer and current_layers != required_layers)
            or current_config["Environment"]["Variables"] != env_vars
        ):
            LOG.info(f"Configuration for {name} changed, updating function")
            client.update_function_configuration(
                FunctionName=name,
                Layers=required_layers,
                Timeout=config.service.lambda_timeout,  # TODO make per-function?
                MemorySize=config.service.lambda_memory,
                Environment=dict(Variables=env_vars),
            )
            needs_publish = True

        return needs_publish

    @classmethod
    def create(cls, config):
        client = get_client(config, "lambda")
        # TODO maybe - per-function roles
        role_arn = ExecutionRole.get_arn(config)
        name = cls.resource_name(config)

        # docs: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.create_function
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
            MemorySize=config.service.lambda_memory,
            Layers=cls.src_layers_list(config) if cls.needs_src_layer else [],
            Environment=dict(Variables=cls.get_environment_variables(config)),
        )
        LOG.info(f"Created function {name}")

    @classmethod
    def get_environment_variables(cls, config):
        # TODO make env per-function?
        if config.service.env.exists():
            with open(config.service.env) as f:
                user_env = dict(line.strip().split("=") for line in f.readlines())
        else:
            user_env = {}

        return {
            "TEAL_SESSION_TTL": "3600",
            "DYNAMODB_TABLE": DataTable.resource_name(config),
            "USE_LIVE_AWS": "foo",  # setting this to "yes" breaks AWS...?
            "RESUME_FN_NAME": FnResume.resource_name(config),
            **user_env,
        }

    @classmethod
    def destroy_if_exists(cls, config):
        client = get_client(config, "lambda")
        name = cls.resource_name(config)
        try:
            client.delete_function(FunctionName=name)
            LOG.info(f"Deleted function {name}")
        except client.exceptions.ResourceNotFoundException:
            pass

    @classmethod
    def invoke(cls, config, data: dict) -> Tuple[str, str]:
        client = get_client(config, "lambda")
        name = cls.resource_name(config)

        payload = bytes(json.dumps(data), "utf-8")

        if not payload:
            payload = bytes("", "utf-8")

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#Lambda.Client.invoke
        response = client.invoke(
            FunctionName=name,
            InvocationType="RequestResponse",
            Payload=payload,
            LogType="Tail",
        )

        if not 200 <= response["StatusCode"] < 300:
            raise InvokeError(response)

        logs = base64.b64decode(response["LogResult"]).decode()
        payload = response["Payload"].read().decode("utf-8")

        return logs, json.loads(payload)


class FnSetexe(TealFunction):
    name = "set_exe"
    handler = "teal_lang.run.aws.set_exe"


class FnNew(TealFunction):
    name = "new"
    handler = "teal_lang.run.aws.new"
    needs_src_layer = True


class FnResume(TealFunction):
    name = "resume"
    handler = "teal_lang.run.aws.resume"
    needs_src_layer = True


class FnEventHandler(TealFunction):
    name = "event_handler"
    handler = "teal_lang.run.aws.event_handler"
    needs_src_layer = True


class FnGetOutput(TealFunction):
    name = "getoutput"
    handler = "teal_lang.run.aws.getoutput"


class FnGetEvents(TealFunction):
    name = "getevents"
    handler = "teal_lang.run.aws.getevents"


class FnVersion(TealFunction):
    name = "version"
    handler = "teal_lang.run.aws.version"


## optional infrastructure


class Trigger:
    pass


@dataclass
class BucketTrigger:
    bucket: str

    def resource_name(self, config):
        return f"teal-{config.service.deployment_id}"

    def _get_filter(self, config):
        try:
            trigger_config = next(
                b for b in config.service.upload_triggers if b.name == self.bucket
            )
        except StopIteration:
            return None
        return dict(
            Key=dict(
                FilterRules=[
                    dict(Name="Prefix", Value=trigger_config.prefix),
                    dict(Name="Suffix", Value=trigger_config.suffix),
                ]
            )
        )

    def _get_current(self, config) -> dict:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.get_bucket_notification_configuration
        client = get_client(config, "s3")
        res = client.get_bucket_notification_configuration(Bucket=self.bucket)
        current = {}

        for key in [
            "LambdaFunctionConfigurations",
            "TopicConfigurations",
            "QueueConfigurations",
        ]:
            try:
                current[key] = res[key]
            except KeyError:
                pass

        return current

    def exists(self, config):
        res = self._get_current(config)
        arn = FnEventHandler.get_arn(config)
        if "LambdaFunctionConfigurations" in res:
            for fn in res["LambdaFunctionConfigurations"]:
                if fn["LambdaFunctionArn"] == arn and fn["Filter"] == self._get_filter(
                    config
                ):
                    return True
        return False

    def trigger_permission_id(self, config):
        """StatementID of the permission added to the event handler lambda"""
        return f"teal-s3-trigger-{self.bucket}"

    def create(self, config):
        client = get_client(config, "s3")
        arn = FnEventHandler.get_arn(config)
        new = self._get_current(config)
        name = self.resource_name(config)

        new_notification = dict(
            Id=name,
            LambdaFunctionArn=arn,
            Events=["s3:ObjectCreated:*"],
            Filter=self._get_filter(config),
        )

        # Add or update the Lambda handler
        if "LambdaFunctionConfigurations" not in new:
            new["LambdaFunctionConfigurations"] = [new_notification]
        else:
            for idx, notification in enumerate(new["LambdaFunctionConfigurations"]):
                if notification["LambdaFunctionArn"] == arn:
                    new["LambdaFunctionConfigurations"][idx] = new_notification
                    break
            else:
                new.append(new_notification)

        # Add the lambda permission. NOTE: this MUST be configured before adding
        # the notification
        lambda_client = get_client(config, "lambda")
        handler_name = FnEventHandler.resource_name(config)
        lambda_client.add_permission(
            FunctionName=handler_name,
            StatementId=self.trigger_permission_id(config),
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{self.bucket}",
            # SourceAccount="", # TODO get this account ID
        )

        # Actually add the notification
        client.put_bucket_notification_configuration(
            Bucket=self.bucket, NotificationConfiguration=new
        )
        LOG.info(f"Added bucket notification from {self.bucket}")

    def destroy_if_exists(self, config, definitely_exists=False):
        if not self.exists(config):
            return
        client = get_client(config, "s3")
        current = self._get_current(config)
        arn = FnEventHandler.get_arn(config)

        # remove just this key
        new_fn_config = [
            fn
            for fn in current["LambdaFunctionConfigurations"]
            if fn["LambdaFunctionArn"] != arn
        ]
        current["LambdaFunctionConfigurations"] = new_fn_config
        client.put_bucket_notification_configuration(
            Bucket=self.bucket, NotificationConfiguration=current
        )

        # And remove the lambda invoke permission
        lambda_client = get_client(config, "lambda")
        handler_name = FnEventHandler.resource_name(config)
        lambda_client.remove_permission(
            FunctionName=handler_name, StatementId=self.trigger_permission_id(config),
        )
        LOG.info(f"Destroyed {self}")

    def create_or_update_or_destroy(self, config):
        exists = self.exists(config)
        needed = False
        for bucket in config.service.upload_triggers:
            if bucket.name == self.bucket:
                needed = True

        if needed:
            if not exists:
                self.create(config)
                LOG.info(f"Created/updated {self}")
        else:
            self.destroy_if_exists(config)


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewayv2.html#client
class SharedAPIGateway:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.service.deployment_id}"

    @staticmethod
    def retrieve(config):
        client = get_client(config, "apigatewayv2")
        name = SharedAPIGateway.resource_name(config)
        items = client.get_apis()["Items"]
        for item in items:
            if item["Name"] == name:
                return item
        return None

    @staticmethod
    def exists(config):
        return SharedAPIGateway.retrieve(config) is not None

    @staticmethod
    def create_or_update(config):
        if api := SharedAPIGateway.retrieve(config):
            SharedAPIGateway.update(config, api)
        else:
            api = SharedAPIGateway.create(config)
        endpoint = api["ApiEndpoint"]
        LOG.info(f"API Endpoint: {endpoint}")

    @staticmethod
    def destroy_if_exists(config):
        if not (api := SharedAPIGateway.retrieve(config)):
            return

        client = get_client(config, "apigatewayv2")
        client.delete_api(ApiId=api["ApiId"])

        lambda_client = get_client(config, "lambda")
        handler_name = FnEventHandler.resource_name(config)
        lambda_client.remove_permission(
            FunctionName=handler_name, StatementId=SharedAPIGateway.trigger_permission_id(config),
        )

        name = api["Name"]
        LOG.info(f"Deleted API {name}")

    @staticmethod
    def trigger_permission_id(config):
        return "teal-apigateway"

    @staticmethod
    def create(config):
        client = get_client(config, "apigatewayv2")
        name = SharedAPIGateway.resource_name(config)

        # Quick Create is awesome.
        #
        # NOTE: Leave RouteKey default so this API catches everything
        # Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewayv2.html#ApiGatewayV2.Client.create_api
        # Cors: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html
        response = client.create_api(
            Name=name,
            ProtocolType="HTTP",
            Target=FnEventHandler.get_arn(config),
            Description=f"Catch-all handler for Teal {config.service.deployment_id}",
            # CorsConfiguration = dict(
            #     AllowCredentials=False,  # TODO? Not allowed with AllowOrigins=*
            #     AllowOrigins=["*"],  # TODO config this
            #     AllowMethods=["*"],
            #     AllowHeaders=["*"],
            # )
        )

        api_id = response["ApiId"]

        # Allow invocation
        # https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
        lambda_client = get_client(config, "lambda")
        handler_name = FnEventHandler.resource_name(config)
        account_id = "297409317403"  # TODO get this account ID
        lambda_client.add_permission(
            FunctionName=handler_name,
            StatementId=SharedAPIGateway.trigger_permission_id(config),
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{config.service.region}:{account_id}:{api_id}/*/$default",
        )
        LOG.info(f"Created API {name}")
        return response

    @staticmethod
    def update(config, api):
        name = api["Name"]
        LOG.info(f"Updated API {name}")
        # TODO ?? Will become relevant when auth is configurable.


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
    FnEventHandler,
    # TODO combine these three:
    FnGetOutput,
    FnGetEvents,
    FnVersion,
]


def deploy(config):
    """Deploy (or update) infrastructure for this config"""
    if not config.service.deployment_id:
        raise ValueError("Need deployment ID")

    LOG.info(f"Deploying: {config.service.deployment_id}")

    # TODO - could make this faster by letting resource return a list of waiters
    # which are waited on at the end.

    for res in CORE_RESOURCES:
        res.create_or_update(config)

    if config.service.enable_api:
        SharedAPIGateway.create_or_update(config)
    else:
        SharedAPIGateway.destroy_if_exists(config)

    for bucket in config.service.managed_buckets:
        # TODO s3_access should be here too.
        res = BucketTrigger(bucket)
        res.create_or_update_or_destroy(config)


def destroy(config):
    """Destroy infrastructure created for this config"""
    LOG.info(f"Destroying: {config.service.deployment_id}")
    # destroy in reverse order so dependencies go first

    for bucket in config.service.managed_buckets:
        # TODO s3_access should be here too.
        res = BucketTrigger(bucket)
        res.destroy_if_exists(config)

    SharedAPIGateway.destroy_if_exists(config)

    for res in reversed(CORE_RESOURCES):
        res.destroy_if_exists(config)


def show(config):
    """Show infrastructure state"""
    for res in CORE_RESOURCES:
        # TODO only show if deployed
        print(f"- {res.__name__}: {res.resource_name(config)}")


# This is a bit pointless for now - could be a generic cloud interface in the
# future.
@dataclass
class Interface:
    set_exe: type
    new: type
    get_output: type
    get_events: type
    version: type


def get_api() -> Interface:
    # TODO check it's deployed?
    return Interface(FnSetexe, FnNew, FnGetOutput, FnGetEvents, FnVersion)
