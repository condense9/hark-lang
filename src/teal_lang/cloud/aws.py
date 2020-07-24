"""Manage Teal deployments in AWS"""

import base64
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Tuple, Union

import boto3
import botocore
from botocore.client import ClientError

from teal_lang.config_classes import InstanceConfig

from ..config import TEAL_DIST_DATA
from ..exceptions import UnexpectedError, UserResolvableError

LOG = logging.getLogger(__name__)

THIS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class DeployConfig:
    uuid: str
    instance: InstanceConfig
    source_layer_hash: str = None
    source_layer_file: Path = None
    source_layer_url: str = None


class DeploymentFailed(UnexpectedError):
    """Failed to deploy because of some unhandled 3rd party exception"""

    def __init__(self, exc):
        info = sys.exc_info()
        tb = "".join(traceback.format_exception(*info))
        super().__init__(tb)


class InvokeError(UnexpectedError):
    "Failed to invoke function"


@lru_cache
def get_client(aws_service: str):
    """Get a boto3 client for AWS_SERVICE, setting endpoint and region"""
    args = {}

    endpoint_url = os.environ.get("AWS_ENDPOINT", None)
    if endpoint_url:
        args["endpoint_url"] = endpoint_url

    return boto3.client(
        aws_service,
        region_name=get_region(),
        # config=botocore.config.Config(retries={"max_attempts": 0}),
        **args,
    )


@lru_cache
def get_account_id():
    try:
        return os.environ["AWS_ACCOUNT_ID"]
    except KeyError:
        return boto3.client("sts").get_caller_identity().get("Account")


def get_region():
    if "AWS_DEFAULT_REGION" in os.environ:
        return os.environ["AWS_DEFAULT_REGION"]
    elif "AWS_REGION" in os.environ:
        return os.environ["AWS_REGION"]  # Preset in the Lambda env
    else:
        raise UserResolvableError(
            "Could not determine deployment region.",
            "AWS_DEFAULT_REGION or AWS_REGION must be set.",
        )


def hash_file(filename: Path) -> str:
    """Get the hex digest SHA256 hash of a file"""
    with open(filename, "rb") as f:
        return sha256(f.read()).hexdigest()


def to_hexdigest(aws_hash: str):
    """Convert aws style sha256 to match the local style"""
    digest = base64.b64decode(aws_hash)
    return "".join("{:02x}".format(v) for v in digest)


def get_bucket_and_key(s3_path: str) -> Tuple[str, str]:
    """Get a bucket and key from an S3 path"""
    # path = s3://bucket/path/to/code.zip
    path = s3_path[5:]  # remove 's3://'
    s3_bucket = path.split("/")[0]  # up to first /
    s3_key = path[len(s3_bucket) + 1 :]  # everything after bucket
    return s3_bucket, s3_key


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
class DataBucket:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.uuid}"

    @staticmethod
    def exists(config):
        client = get_client("s3")
        name = DataBucket.resource_name(config)
        try:
            client.head_bucket(Bucket=name)
            return True
        except ClientError:
            return False

    @staticmethod
    def create(config):
        name = DataBucket.resource_name(config)
        client = get_client("s3")

        # Example: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-creating-buckets.html
        try:
            location = {"LocationConstraint": get_region()}
            client.create_bucket(
                Bucket=name, ACL="private", CreateBucketConfiguration=location
            )
            LOG.info(f"[+] Created bucket {name}")
        except ClientError as exc:
            raise DeploymentFailed(exc) from exc

    @staticmethod
    def create_or_update(config):
        """Create the data bucket if it doesn't exist"""
        name = DataBucket.resource_name(config)
        client = get_client("s3")
        if not DataBucket.exists(config):
            DataBucket.create(config)

    @staticmethod
    def destroy_if_exists(config):
        name = DataBucket.resource_name(config)
        client = get_client("s3")
        # Delete all objects first (NOTE - assumes no versioning)

        try:
            destroy_bucket(client, name)
            LOG.info(f"[-] Deleted bucket {name}")
        except client.exceptions.NoSuchBucket:
            pass


def destroy_bucket(client, name):
    """Delete all items in the bucket and delete the bucket"""
    objects = client.list_objects(Bucket=name).get("Contents", [])
    delete_keys = {"Objects": [{"Key": k} for k in [obj["Key"] for obj in objects]]}
    if objects:
        client.delete_objects(Bucket=name, Delete=delete_keys)
    client.delete_bucket(Bucket=name)


def upload_if_necessary(client, bucket, key, filename: Path):
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
            LOG.info(f"[+] Uploaded {filename}")

    except ClientError as exc:
        raise DeploymentFailed(exc) from exc


class S3File:
    """A file in S3. This class must be subclassed"""

    @classmethod
    def local_sha(cls, config) -> str:
        return hash_file(cls.local_file)

    @classmethod
    def create_or_update(cls, config):
        """Create the file and upload it"""
        client = get_client("s3")
        bucket = DataBucket.resource_name(config)
        upload_if_necessary(client, bucket, cls.key, cls.local_file)

    @classmethod
    def destroy_if_exists(cls, config):
        client = get_client("s3")
        bucket = DataBucket.resource_name(config)
        try:
            client.delete_object(Bucket=bucket, Key=cls.key)
            LOG.info(f"[-] Deleted {cls.key} from {bucket}")
        except (client.exceptions.NoSuchKey, client.exceptions.NoSuchBucket):
            pass


class TealPackage(S3File):
    key = "teal_lambda.zip"
    local_file = TEAL_DIST_DATA / "teal_lambda.zip"


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#client
class DataTable:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.uuid}"

    @staticmethod
    def exists(config):
        client = get_client("dynamodb")
        name = DataTable.resource_name(config)
        try:
            client.describe_table(TableName=name)
            return True
        except client.exceptions.ResourceNotFoundException:
            return False

    @staticmethod
    def get_arn(config):
        client = get_client("dynamodb")
        name = DataTable.resource_name(config)
        res = client.describe_table(TableName=name)
        return res["Table"]["TableArn"]

    @staticmethod
    def create_or_update(config):
        client = get_client("dynamodb")
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
        LOG.info(f"[+] Created Table {name}")

    @staticmethod
    def destroy_if_exists(config):
        client = get_client("dynamodb")
        name = DataTable.resource_name(config)
        try:
            client.delete_table(TableName=name)
            waiter = client.get_waiter("table_not_exists")
            waiter.wait(TableName=name)
            LOG.info(f"[-] Deleted Table {name}")
        except client.exceptions.ResourceNotFoundException:
            pass


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#client
class ExecutionRole:
    s3_access_policy_name = "s3_access"
    user_policy_name = "user_policy"

    @staticmethod
    def all_managed_policies():
        return [
            "default",
            ExecutionRole.s3_access_policy_name,
            ExecutionRole.user_policy_name,
        ]

    @staticmethod
    def resource_name(config):
        return f"teal-{config.uuid}"

    @staticmethod
    def get_arn(config):
        client = get_client("iam")
        res = client.get_role(RoleName=ExecutionRole.resource_name(config))
        return res["Role"]["Arn"]

    @staticmethod
    def exists(config):
        client = get_client("iam")
        try:
            res = client.get_role(RoleName=ExecutionRole.resource_name(config))
            return True
        except client.exceptions.NoSuchEntityException:
            return False

    @staticmethod
    def destroy_if_exists(config):
        if not ExecutionRole.exists(config):
            return

        client = get_client("iam")
        name = ExecutionRole.resource_name(config)

        for policy_name in ExecutionRole.all_managed_policies():
            try:
                client.delete_role_policy(RoleName=name, PolicyName=policy_name)
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
        LOG.info(f"[-] Deleted execution role {name}")

    @staticmethod
    def update_policy(role_name, policy_name, desired) -> bool:
        """Update (or delete) a role's policy"""
        client = get_client("iam")
        try:
            current = client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            current_statement = current["PolicyDocument"]["Statement"]
        except client.exceptions.NoSuchEntityException:
            current = None

        # Nothing to do
        if current is None and desired is None:
            return False

        # should not exist, but does:
        if current is not None and desired is None:
            client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
            LOG.info(
                f"[-] Removed policy '{policy_name}' for Execution Role {role_name}"
            )
            return True

        should_exist = current is None and desired is not None
        is_different = current and current_statement != desired["Statement"]

        if is_different:
            client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

        if should_exist or is_different:
            client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(desired),
            )
            LOG.info(
                f"[+] Updated policy '{policy_name}' for Execution Role {role_name}"
            )
            return True
        return False

    @staticmethod
    def get_s3_access_policy(config) -> dict:
        if not config.instance.s3_access:
            return None
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:*"],
                    "Resource": [
                        f"arn:aws:s3:::{bucket}/*"
                        for bucket in config.instance.s3_access
                    ],
                }
            ],
        }

    @staticmethod
    def update_s3_access_policy(config) -> bool:
        name = ExecutionRole.resource_name(config)
        policy = ExecutionRole.get_s3_access_policy(config)
        return ExecutionRole.update_policy(
            name, ExecutionRole.s3_access_policy_name, policy
        )

    @staticmethod
    def get_user_policy(config) -> Union[dict, None]:
        if not config.instance.policy_file:
            return None
        if not config.instance.policy_file.exists():
            raise UserResolvableError(
                f"Cannot find policy_file `{config.instance.policy_file}'.",
                "Check configuration.",
            )
        with open(config.instance.policy_file) as f:
            return json.loads(f.read())

    @staticmethod
    def update_user_policy(config) -> bool:
        """Update the policy from config.instance.policy_file"""
        name = ExecutionRole.resource_name(config)
        policy = ExecutionRole.get_user_policy(config)
        return ExecutionRole.update_policy(name, ExecutionRole.user_policy_name, policy)

    @staticmethod
    def create_or_update(config):
        if ExecutionRole.exists(config):
            updates = [
                ExecutionRole.update_s3_access_policy(config),
                ExecutionRole.update_user_policy(config),
            ]
            if any(updates):
                time.sleep(5)  # Allow propagation (see notes below...)
            return

        client = get_client("iam")
        name = ExecutionRole.resource_name(config)
        table_arn = DataTable.get_arn(config)

        basic_policy = {
            "Version": "2012-10-17",
            "Statement": [
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
            RoleName=name, PolicyName="default", PolicyDocument=json.dumps(basic_policy)
        )
        # User configurable policies
        ExecutionRole.update_s3_access_policy(config)
        ExecutionRole.update_user_policy(config)
        # Basic Lambda policy - logs, etc
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
        LOG.info(f"[+] Created Execution Role")


class SourceLayer:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.uuid}-src"

    @staticmethod
    def get_arn(config) -> Union[None, str]:
        """Get ARN and SHA256 of the highest-version layer"""
        client = get_client("lambda")
        name = SourceLayer.resource_name(config)
        res = client.list_layer_versions(LayerName=name, MaxItems=1)
        try:
            return res["LayerVersions"][0]["LayerVersionArn"]
        except IndexError:
            return None

    @staticmethod
    def get_latest_sha256(config) -> Union[None, str]:
        """Get ARN and SHA256 of the highest-version layer"""
        client = get_client("lambda")
        arn = SourceLayer.get_arn(config)
        if arn:
            res = client.get_layer_version_by_arn(Arn=arn)
            return to_hexdigest(res["Content"]["CodeSha256"])

    @staticmethod
    def create_or_update(config):
        current_sha = SourceLayer.get_latest_sha256(config)
        local_sha = config.source_layer_hash

        if local_sha is not None and local_sha == current_sha:
            return

        if config.source_layer_file:
            # upload the new source package
            s3_bucket = DataBucket.resource_name(config)
            s3_key = f"automated/source_{config.source_layer_hash}.zip"
            client = get_client("s3")
            upload_if_necessary(client, s3_bucket, s3_key, config.source_layer_file)
            LOG.info(f"[+] Uploaded source layer {config.source_layer_file}")
        else:
            s3_bucket, s3_key = get_bucket_and_key(config.source_layer_url)

        client = get_client("lambda")
        name = SourceLayer.resource_name(config)
        client.publish_layer_version(
            LayerName=name, Content=dict(S3Bucket=s3_bucket, S3Key=s3_key)
        )
        current_sha = SourceLayer.get_latest_sha256(config)
        assert current_sha == local_sha
        LOG.info(f"[+] Published new version of layer {name}")

    @staticmethod
    def destroy_if_exists(config):
        client = get_client("lambda")
        name = SourceLayer.resource_name(config)
        while True:
            versions = client.list_layer_versions(LayerName=name)
            if not versions["LayerVersions"]:
                break
            for v in versions["LayerVersions"]:
                number = v["Version"]
                client.delete_layer_version(LayerName=name, VersionNumber=number)
                LOG.info(f"[-] Deleted layer {name} v{number}")


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html#client
class TealFunction:
    needs_src_layer = False

    @classmethod
    def create_extra_permissions(cls, config):
        pass

    @classmethod
    def resource_name(cls, config):
        return f"teal-{config.uuid}-{cls.name}"

    @classmethod
    def exists(cls, config):
        client = get_client("lambda")
        name = cls.resource_name(config)
        try:
            res = client.get_function(FunctionName=name)
            return True
        except client.exceptions.ResourceNotFoundException:
            return False

    @classmethod
    def get_arn(cls, config):
        """Get the ARN, or None if it doesn't exist"""
        client = get_client("lambda")
        name = cls.resource_name(config)
        try:
            res = client.get_function(FunctionName=name)
            return res["Configuration"]["FunctionArn"]
        except client.exceptions.ResourceNotFoundException:
            return None

    @classmethod
    def src_layers_list(cls, config):
        """Create the list of layers to provide user src code"""
        # NOTE: if the "extra" layers come last, you may get error: "Layer
        # conversion failed: Some files need to be overridden by layers but
        # don't have write permissions;". Fixed by putting extra layers first.
        # Don't fully understand it though. See also:
        # https://forums.aws.amazon.com/thread.jspa?messageID=908553
        return list(config.instance.extra_layers) + [SourceLayer.get_arn(config)]

    @classmethod
    def create_or_update(cls, config):
        if cls.exists(config):
            needs_publish = cls.update(config)
        else:
            cls.create(config)
            needs_publish = True

        if needs_publish:
            client = get_client("lambda")
            name = cls.resource_name(config)
            client.publish_version(FunctionName=name)

            waiter = client.get_waiter("function_active")
            waiter.wait(FunctionName=name)

    @classmethod
    def update(cls, config) -> bool:
        client = get_client("lambda")
        name = cls.resource_name(config)
        needs_publish = False
        current_config = client.get_function_configuration(FunctionName=name)

        # Check if Teal code needs to be updated
        current_sha = to_hexdigest(current_config["CodeSha256"])
        required_sha = TealPackage.local_sha(config)

        if current_sha != required_sha:
            LOG.info(f"[+] Code for {name} changed, updating function")
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
            current_config["MemorySize"] != config.instance.lambda_memory
            or current_config["Timeout"] != config.instance.lambda_timeout
            or (cls.needs_src_layer and current_layers != required_layers)
            or current_config["Environment"]["Variables"] != env_vars
        ):
            LOG.info(f"[+] Configuration for {name} changed, updating function")
            client.update_function_configuration(
                FunctionName=name,
                Layers=required_layers,
                Timeout=config.instance.lambda_timeout,  # TODO make per-function?
                MemorySize=config.instance.lambda_memory,
                Environment=dict(Variables=env_vars),
            )
            needs_publish = True

        return needs_publish

    @classmethod
    def create(cls, config):
        client = get_client("lambda")
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
            Timeout=config.instance.lambda_timeout,  # TODO make per-function?
            MemorySize=config.instance.lambda_memory,
            Layers=cls.src_layers_list(config) if cls.needs_src_layer else [],
            Environment=dict(Variables=cls.get_environment_variables(config)),
        )
        LOG.info(f"[+] Created function {name}")

    @classmethod
    def get_environment_variables(cls, config):
        # TODO make env per-function?
        if config.instance.env.exists():
            with open(config.instance.env) as f:
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
        client = get_client("lambda")
        name = cls.resource_name(config)
        try:
            client.delete_function(FunctionName=name)
            LOG.info(f"[-] Deleted function {name}")
        except client.exceptions.ResourceNotFoundException:
            pass

    @classmethod
    def invoke(cls, config, data: dict) -> Tuple[str, str]:
        if not config.uuid:
            raise UnexpectedError("No Instance UUID configured")

        client = get_client("lambda")
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


@dataclass
class BucketTrigger:
    bucket: str

    def resource_name(self, config):
        return f"teal-{config.uuid}"

    def _get_filter(self, config):
        try:
            trigger_config = next(
                b for b in config.instance.upload_triggers if b.name == self.bucket
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
        client = get_client("s3")
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
        if not arn:  # If the function doesn't exist, assume the trigger doesn't
            return False
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
        client = get_client("s3")
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
                # Modify an existing trigger
                if notification["LambdaFunctionArn"] == arn:
                    new["LambdaFunctionConfigurations"][idx] = new_notification
                    break
            else:
                # Or add a new one
                new["LambdaFunctionConfigurations"].append(new_notification)

        # Add the lambda permission. NOTE: this MUST be configured before adding
        # the notification
        lambda_client = get_client("lambda")
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
        LOG.info(f"[+] Created/updated {self}")

    def destroy_if_exists(self, config, definitely_exists=False):
        if not self.exists(config):
            return
        client = get_client("s3")
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
        lambda_client = get_client("lambda")
        handler_name = FnEventHandler.resource_name(config)
        lambda_client.remove_permission(
            FunctionName=handler_name, StatementId=self.trigger_permission_id(config),
        )
        LOG.info(f"[-] Destroyed {self}")

    def create_or_update(self, config):
        """Create or update (or destroy) this"""
        exists = self.exists(config)
        needed = False
        for bucket in config.instance.upload_triggers:
            if bucket.name == self.bucket:
                needed = True

        if needed:
            if not exists:
                self.create(config)
        else:
            self.destroy_if_exists(config)


# Client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewayv2.html#client
class SharedAPIGateway:
    @staticmethod
    def resource_name(config):
        return f"teal-{config.uuid}"

    @staticmethod
    def retrieve(config):
        client = get_client("apigatewayv2")
        name = SharedAPIGateway.resource_name(config)
        items = client.get_apis()["Items"]
        for item in items:
            if item["Name"] == name:
                return item
        return None

    @staticmethod
    def get_endpoint(config) -> Union[None, str]:
        api = SharedAPIGateway.retrieve(config)
        if api:
            return api["ApiEndpoint"]

    @staticmethod
    def exists(config):
        return SharedAPIGateway.retrieve(config) is not None

    @staticmethod
    def create_or_update(config):
        if not config.instance.enable_api:
            SharedAPIGateway.destroy_if_exists(config)
        else:
            api = SharedAPIGateway.retrieve(config)
            if api:
                SharedAPIGateway.update(config, api)
            else:
                api = SharedAPIGateway.create(config)
            endpoint = api["ApiEndpoint"]
            LOG.info(f"API Endpoint: {endpoint}")
            print(f"\nAPI Endpoint: {endpoint}")

    @staticmethod
    def destroy_if_exists(config):
        api = SharedAPIGateway.retrieve(config)
        if not api:
            return

        client = get_client("apigatewayv2")
        client.delete_api(ApiId=api["ApiId"])

        lambda_client = get_client("lambda")
        handler_name = FnEventHandler.resource_name(config)
        try:
            lambda_client.remove_permission(
                FunctionName=handler_name,
                StatementId=SharedAPIGateway.trigger_permission_id(config),
            )
        except lambda_client.exceptions.ResourceNotFoundException:
            pass

        name = api["Name"]
        LOG.info(f"[-] Deleted API {name}")

    @staticmethod  # It might depend on config in the future
    def trigger_permission_id(config):
        return "teal-apigateway"

    @staticmethod
    def create(config):
        client = get_client("apigatewayv2")
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
            Description=f"Catch-all handler for Teal {config.uuid}",
            # CorsConfiguration = dict(
            #     AllowCredentials=False,  # TODO? Not allowed with AllowOrigins=*
            #     AllowOrigins=["*"],  # TODO config this
            #     AllowMethods=["*"],
            #     AllowHeaders=["*"],
            # )
        )

        api_id = response["ApiId"]

        # Update payload type most things don't work with the new version :(
        integration = client.get_integrations(ApiId=api_id)["Items"][0]
        client.update_integration(
            ApiId=api_id,
            IntegrationId=integration["IntegrationId"],
            PayloadFormatVersion="1.0",
        )

        # Allow invocation
        # https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html
        lambda_client = get_client("lambda")
        handler_name = FnEventHandler.resource_name(config)
        region = get_region()
        account_id = get_account_id()
        lambda_client.add_permission(
            FunctionName=handler_name,
            StatementId=SharedAPIGateway.trigger_permission_id(config),
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/$default",
        )
        LOG.info(f"[+] Created API {name}")
        return response

    @staticmethod
    def update(config, api):
        name = api["Name"]
        LOG.info(f"[+] Updated API {name}")
        # TODO ?? Will become relevant when auth is configurable.


CORE_RESOURCES = [
    DataBucket,
    TealPackage,
    DataTable,
    ExecutionRole,
    SourceLayer,
    FnSetexe,
    FnResume,
    FnEventHandler,
    # TODO combine these three:
    FnGetOutput,
    FnGetEvents,
    FnVersion,
    SharedAPIGateway,
]


def _get_resources(config) -> list:
    resources = CORE_RESOURCES

    for bucket in config.instance.managed_buckets:
        # TODO s3_access should be here too.
        resources.append(BucketTrigger(bucket))

    for item in config.instance.upload_triggers:
        if item.name not in config.instance.managed_buckets:
            print(
                f"WARNING: '{item.name}' is not in instance.managed_buckets - no action will be taken."
            )

    return resources


def deploy(config, callback_start=None):
    """Deploy (or update) infrastructure for this config"""
    if not config.uuid:
        raise UnexpectedError("No Instance UUID configured")

    # One of these must be set...
    if config.source_layer_url is None and config.source_layer_file is None:
        raise UnexpectedError("No source layer configured")

    # Vague file-format validation
    if config.source_layer_file and not str(config.source_layer_file).endswith(".zip"):
        raise UserResolvableError(
            f"{config.source_layer_file} is not a .zip file",
            "The Python source layer must be packaged as a zip file.",
        )

    LOG.info(f"Deploying Instance: {config.uuid}")

    # TODO - could make this faster by letting resource return a list of waiters
    # which are waited on at the end.

    for res in _get_resources(config):
        LOG.info(f"Resource: {res}")
        if callback_start:
            callback_start(res)
        res.create_or_update(config)


def destroy(config, callback_start=None):
    """Destroy infrastructure created for this config"""
    if not config.uuid:
        raise UnexpectedError("No Instance UUID configured")

    LOG.info(f"Destroying Instance: {config.uuid}")

    # destroy in reverse order so dependencies go first
    for res in reversed(_get_resources(config)):
        LOG.info(f"Resource: {res}")
        if callback_start:
            callback_start(res)
        res.destroy_if_exists(config)


def show(config):
    """Show infrastructure state"""
    for res in _get_resources(config):
        # TODO only show if deployed
        print(f"- {res.__name__}: {res.resource_name(config)}")
