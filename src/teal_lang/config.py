"""Teal configuration loading"""

import logging
import os
import uuid
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import boto3
import toml

LOG = logging.getLogger(__name__)

# NOTE: we could have a "[service.prod]" section with production overrides, and
# a CLI flag to switch


@dataclass(frozen=True)
class BucketTriggerConfig:
    name: str
    prefix: str
    suffix: str


@dataclass(frozen=True)
class ServiceConfig:
    region: str
    python_src: Path
    python_requirements: Path
    deployment_id: str
    data_dir: Path
    lambda_timeout: int
    lambda_memory: int
    teal_file: str
    extra_layers: tuple
    env: Path
    s3_access: tuple
    upload_triggers: Tuple[BucketTriggerConfig]
    managed_buckets: list


@dataclass(frozen=True)
class Config:
    root: str
    service: ServiceConfig


SERVICE_DEFAULTS = dict(
    python_src="src",
    python_requirements="requirements.txt",
    data_dir=".teal",
    lambda_timeout=240,
    lambda_memory=128,
    teal_file="service.tl",
    env="teal_env.txt",
    extra_layers=[],
    s3_access=[],
    upload_triggers=[],
    managed_buckets=[],
)

DEFAULT_CONFIG_FILENAME = Path("teal.toml")
DEPLOYMENT_ID_FILE = "teal_deployment_id"


class ConfigError(Exception):
    """Error loading configuration"""


def _create_deployment_id(service):
    """Make a random deployment ID and save it"""
    # only taking 16 chars to make it more readable
    did = uuid.uuid4().hex[:16]
    LOG.info(f"Using new deployment ID {did}")

    did_file = service["data_dir"] / DEPLOYMENT_ID_FILE
    LOG.info(f"Writing deployment ID to {did_file}")

    # Ensure the data directory exists
    os.makedirs(str(service["data_dir"]), exist_ok=True)

    with open(str(did_file), "w") as f:
        f.write(did)

    return did


def _get_deployment_id(service: dict, create_deployment_id: bool) -> str:
    """Try to find a deployment ID"""
    did_file = service["data_dir"] / DEPLOYMENT_ID_FILE
    if did_file.exists():
        with open(str(did_file), "r") as f:
            return f.read().strip()

    if it := os.environ.get("TEAL_DEPLOYMENT_ID", None):
        return it

    if create_deployment_id:
        return _create_deployment_id(service)

    raise ConfigError("Can't find a deployment ID")


def load(
    config_file: Path = None, *, load_deployment_id=False, create_deployment_id=False
) -> Config:
    """Load the configuration, creating a new deployment ID if desired"""
    if not config_file:
        config_file = DEFAULT_CONFIG_FILENAME

    try:
        data = toml.load(config_file)
    except FileNotFoundError:
        LOG.info(f"{config_file} not found, using default service configuration")
        service = SERVICE_DEFAULTS
    else:
        try:
            service = data["service"]
        except KeyError:
            raise ConfigError(f"No [service] section in {config_file}")

        for key, value in SERVICE_DEFAULTS.items():
            if key not in service:
                service[key] = value
                LOG.info(f"Using default for `{key}`: {value}")

    # ensure some keys are paths
    for key in ["python_src", "python_requirements", "env", "data_dir"]:
        service[key] = Path(service[key])

    # lists are not hashable, and Config must be hashable
    for key in ["extra_layers", "s3_access", "managed_buckets"]:
        service[key] = tuple(service[key])

    if not service.get("region", None):
        session = boto3.session.Session()
        service["region"] = session.region_name

    # TODO get deployment_id from CLI arg?
    if load_deployment_id:
        service["deployment_id"] = _get_deployment_id(service, create_deployment_id)
    else:
        service["deployment_id"] = None

    service["upload_triggers"] = tuple(
        BucketTriggerConfig(*val) for val in service["upload_triggers"]
    )

    root = config_file.parent.resolve()
    return Config(root=root, service=ServiceConfig(**service))
