"""Load Teal configuration"""

import logging
import os
import shutil
import uuid
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

import boto3
import toml

from .config_classes import InstanceConfig, ProjectConfig
from .exceptions import UserResolvableError

LOG = logging.getLogger(__name__)

TEAL_DIST_DATA = Path(__file__).parent / "dist_data"
DEFAULT_CONFIG_FILEPATH = Path("teal.toml")
DEFAULT_UUID_FILENAME = "instance_uuid.txt"
DEFAULT_PROJECTID_FILENAME = "project_id.txt"


class ConfigError(UserResolvableError):
    """Error loading configuration"""


LAST_LOADED = None


@dataclass
class Config:
    root: str
    config_file: Path
    # The following two options determine whether the deployment target is
    # self-hosted or teal cloud
    project_id: Union[str, None]
    instance_uuid: Union[uuid.UUID, None]
    project: ProjectConfig
    instance: InstanceConfig
    endpoint: Union[str, None]  # TODO provide a default
    instance_name: str = "dev"


def get_last_loaded() -> Config:
    return LAST_LOADED


def load(args: dict) -> Config:
    """Load the configuration, creating a new deployment ID if desired"""
    if args["--config"]:
        config_file = Path(args["--config"])
    else:
        config_file = DEFAULT_CONFIG_FILEPATH

    project_root = config_file.parent.resolve()

    try:
        data = toml.load(config_file)
    except FileNotFoundError:
        raise ConfigError(
            f"{config_file} not found",
            "Either create it manually, or use `teal init' to generate a new one.",
        )

    if "project" not in data:
        raise ConfigError(
            f"No [project] section in {config_file}",
            "Check out an example of what the config file should look like:\n"
            "https://github.com/condense9/teal-lang/blob/master/examples/fractals/teal.toml",
        )

    project_config = ProjectConfig(**data.pop("project"))
    instance_config = InstanceConfig(**data.pop("instance", {}))

    # make the data dir absolute
    if not project_config.data_dir.is_absolute():
        project_config.data_dir = (project_root / project_config.data_dir).resolve()

    # and make sure it exists
    if not project_config.data_dir.is_dir():
        os.makedirs(str(project_config.data_dir))

    global LAST_LOADED
    LAST_LOADED = Config(
        root=project_root,
        config_file=config_file,
        project=project_config,
        instance=instance_config,
        endpoint=os.environ.get("TEAL_CLOUD_ENDPOINT", None),
        instance_uuid=_try_get_instance_uuid(args, project_config.data_dir),
        project_id=_try_get_project_id(project_config.data_dir),
        instance_name=args["--name"],
    )
    return LAST_LOADED


def _try_get_instance_uuid(args, data_dir: Path) -> Union[uuid.UUID, None]:
    """Get the instance UUID if it exists"""
    if args["--uuid"]:
        return args["--uuid"]
    filename = data_dir / DEFAULT_UUID_FILENAME
    if data_dir.exists() and filename.exists():
        with open(filename) as f:
            return uuid.UUID(f.read().strip())


def save_instance_uuid(config: Config, value: str):
    """Save an instance UUID in the project data"""
    data_dir = config.project.data_dir
    if not data_dir.exists():
        os.makedirs(data_dir)
    uuid_file = data_dir / DEFAULT_UUID_FILENAME
    with open(uuid_file, "w") as f:
        f.write(str(value))


def new_instance_uuid(config: Config) -> uuid.UUID:
    """Make and save an instance UUID"""
    data_dir = config.project.data_dir
    value = uuid.uuid4()
    save_instance_uuid(config, value)
    LOG.info("New instance: %s", value)
    return value


def _try_get_project_id(data_dir: Path) -> Union[str, None]:
    """Get the project ID if it exists"""
    filename = data_dir / DEFAULT_PROJECTID_FILENAME
    if data_dir.exists() and filename.exists():
        with open(filename) as f:
            return f.read().strip()


def save_project_id(config: Config, project_id: int):
    """Save the project ID in the project data"""
    data_dir = config.project.data_dir
    filename = data_dir / DEFAULT_PROJECTID_FILENAME
    with open(filename, "w") as f:
        return f.write(str(project_id))


def create_skeleton(dest="."):
    """Create a skeleton (template) config file in the given dir"""
    filename = Path(dest) / DEFAULT_CONFIG_FILEPATH
    if filename.exists():
        raise UserResolvableError(
            f"{filename} already exists", "Cowardly refusing to clobber it...",
        )
    shutil.copyfile(TEAL_DIST_DATA / DEFAULT_CONFIG_FILEPATH, filename)
