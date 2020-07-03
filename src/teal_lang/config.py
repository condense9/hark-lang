"""Load Teal configuration"""

import functools
import logging
import os
import uuid
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

import boto3
import toml

from .config_classes import InstanceConfig, ProjectConfig

LOG = logging.getLogger(__name__)

DEFAULT_CONFIG_FILEPATH = Path("teal.toml")
DEFAULT_UUID_FILENAME = "instance_uuid.txt"
DEFAULT_PROJECTID_FILENAME = "project_id.txt"


class ConfigError(Exception):
    """Error loading configuration"""


@dataclass
class Config:
    root: str
    project: ProjectConfig
    instance: InstanceConfig
    endpoint: Union[str, None]
    instance_uuid: Union[uuid.UUID, None]
    project_id: Union[str, None]


@functools.lru_cache
def load(config_file: Path = None) -> Config:
    """Load the configuration, creating a new deployment ID if desired"""
    if not config_file:
        config_file = DEFAULT_CONFIG_FILEPATH

    project_root = config_file.parent.resolve()

    try:
        data = toml.load(config_file)
    except FileNotFoundError:
        raise ConfigError(f"{config_file} not found")

    if "project" not in data:
        raise ConfigError(f"No [project] section in {config_file}")

    project_config = ProjectConfig(**data.pop("project"))
    instance_config = InstanceConfig(**data.pop("instance", {}))

    # make the data dir absolute
    if not project_config.data_dir.is_absolute():
        project_config.data_dir = (project_root / project_config.data_dir).resolve()

    # and make sure it exists
    if not project_config.data_dir.is_dir():
        os.makedirs(str(project_config.data_dir))

    return Config(
        root=project_root,
        project=project_config,
        instance=instance_config,
        endpoint=os.environ.get("TEAL_CLOUD_ENDPOINT", None),
        instance_uuid=_try_get_instance_uuid(project_config.data_dir),
        project_id=_try_get_project_id(project_config.data_dir),
    )


def _try_get_instance_uuid(data_dir: Path) -> Union[uuid.UUID, None]:
    """Get the instance UUID if it exists"""
    filename = data_dir / DEFAULT_UUID_FILENAME
    if data_dir.exists() and filename.exists():
        with open(filename) as f:
            return uuid.UUID(f.read())


def _try_get_project_id(data_dir: Path) -> Union[str, None]:
    """Get the project ID if it exists"""
    filename = data_dir / DEFAULT_PROJECTID_FILENAME
    if data_dir.exists() and filename.exists():
        with open(filename) as f:
            return f.read()


def new_instance_uuid(config: Config) -> uuid.UUID:
    """Make and save an instance UUID"""
    data_dir = config.project.data_dir
    value = uuid.uuid4()

    if not data_dir.exists():
        os.makedirs(data_dir)

    uuid_file = data_dir / DEFAULT_UUID_FILENAME

    with open(uuid_file, "w") as f:
        f.write(str(value))

    LOG.info("New instance: %s", cfg.instance_uuid)
    return value
