"""Teal configuration loading"""

from dataclasses import dataclass
from pathlib import Path
import toml
import logging

LOG = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    name: str
    region: str
    teal_version: str
    python_src: Path
    python_deps: Path
    provider: str
    deployment_id_file: Path
    deployment_id: str


@dataclass(frozen=True)
class Config:
    service: ServiceConfig


DEFAULTS = dict(
    teal_version=None,
    python_src="src",
    python_deps="requirements.txt",
    provider="aws",
    region=None,
    deployment_id_file=".teal_deployment_id",
    deployment_id=None,
)

DEFAULT_CONFIG_FILENAME = Path("teal.toml")


class ConfigError(Exception):
    """Error loading configuration"""


def load(config_file: Path = None) -> Config:
    """Load the configuration"""
    if not config_file:
        config_file = DEFAULT_CONFIG_FILENAME

    data = toml.load(config_file)

    try:
        service = data["service"]
    except KeyError:
        raise ConfigError(f"No [service] section in {config_file}")

    for key, value in DEFAULTS.items():
        if key not in service:
            service[key] = value
            LOG.info(f"Using default for `{key}`: {value}")

    # TODO get deployment_id from CLI arg?

    return Config(service=ServiceConfig(**service))
