"""Teal configuration loading"""

from dataclasses import dataclass
from pathlib import Path
import toml
import logging


@dataclass(frozen=True)
class ServiceConfig:
    name: str
    region: str
    teal_version: str
    python_src: Path
    python_deps: Path
    provider: str


@dataclass(frozen=True)
class Config:
    service: ServiceConfig


DEFAULTS = dict(
    # --
    teal_version=None,
    python_src="src",
    python_deps="requirements.txt",
    provider="aws",
    region=None,
)

LOCAL_CONFIG_FILENAME = Path("teal.toml")

LOG = logging.getLogger(__name__)


class ConfigError(Exception):
    """Error loading configuration"""


def load() -> Config:
    """Load the configuration"""
    data = toml.load(LOCAL_CONFIG_FILENAME)

    try:
        service = data["service"]
    except KeyError:
        raise ConfigError(f"No [service] section in {LOCAL_CONFIG_FILENAME}")

    for key, value in DEFAULTS.items():
        if key not in service:
            service[key] = value
            LOG.info(f"Using default for `{key}`")

    return Config(service=ServiceConfig(**service))
