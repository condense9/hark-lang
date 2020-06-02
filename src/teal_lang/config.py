"""Teal configuration loading"""

import logging
from dataclasses import dataclass
from pathlib import Path

import boto3
import toml

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    region: str
    teal_version: str
    python_src: str
    python_deps: str
    provider: str
    deployment_id_file: str
    deployment_id: str
    data_dir: str
    lambda_timeout: int
    teal_file: str


@dataclass(frozen=True)
class Config:
    root: str
    service: ServiceConfig


SERVICE_DEFAULTS = dict(
    teal_version=None,
    python_src="src",
    python_deps="requirements.txt",
    provider="aws",
    data_dir=".teal_data",
    deployment_id_file=".teal_deployment_id",
    lambda_timeout=240,
    teal_file="service.tl",
)

DEFAULT_CONFIG_FILENAME = Path("teal.toml")


class ConfigError(Exception):
    """Error loading configuration"""


def _create_deployment_id(config):
    """Make a random deployment ID"""
    # only taking 16 chars to make it more readable
    did = uuid.uuid4().hex[:16]
    LOG.info(f"Using new deployment ID {did}")

    did_file = Path(config.service.deployment_id_file)
    LOG.info(f"Writing deployment ID to {did_file}")

    with open(str(did_file), "w") as f:
        f.write(did)

    config.service.deployment_id = did


def _get_deployment_id(service: dict, create_deployment_id: bool) -> str:
    """Try to find a deployment ID"""
    already_exists = service.get("deployment_id", None)
    if already_exists:
        return already_exists

    did_file = Path(service["deployment_id_file"])
    if did_file.exists():
        with open(str(did_file), "r") as f:
            return f.read().strip()

    id_from_env = os.environ.get("TEAL_DEPLOYMENT_ID", None)
    if id_from_env:
        return id_from_env

    if create_deployment_id:
        return _create_deployment_id(config)

    raise ConfigError("Can't find a deployment ID")


def load(config_file: Path = None, *, create_deployment_id=False) -> Config:
    """Load the configuration"""
    if not config_file:
        config_file = DEFAULT_CONFIG_FILENAME

    data = toml.load(config_file)

    try:
        service = data["service"]
    except KeyError:
        raise ConfigError(f"No [service] section in {config_file}")

    for key, value in SERVICE_DEFAULTS.items():
        if key not in service:
            service[key] = value
            LOG.info(f"Using default for `{key}`: {value}")

    # TODO get deployment_id from CLI arg?

    if not service.get("region", None):
        session = boto3.session.Session()
        service["region"] = session.region_name

    service["deployment_id"] = _get_deployment_id(service, create_deployment_id)

    root = config_file.parent.resolve()
    return Config(root=root, service=ServiceConfig(**service))
