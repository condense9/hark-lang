"""Teal configuration data, usually stored in teal.toml"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

# Constants
DEFAULT_TEAL_FILE = "service.tl"
DEFAULT_ENV_FILE = "teal_env.txt"
DEFAULT_REQUIREMENTS_FILE = "requirements.txt"
DEFAULT_DATA_DIR = ".teal"
DEFAULT_PYTHON_SOURCE_DIR = "src"


@dataclass(unsafe_hash=True)
class ProjectConfig:
    teal_file: str = Path(DEFAULT_TEAL_FILE)
    python_src: Path = Path(DEFAULT_PYTHON_SOURCE_DIR)
    python_requirements: Path = Path(DEFAULT_REQUIREMENTS_FILE)
    data_dir: Path = Path(DEFAULT_DATA_DIR)

    def __post_init__(self):
        # ensure some keys are paths
        for key in ["python_src", "python_requirements", "data_dir", "teal_file"]:
            setattr(self, key, Path(getattr(self, key)))


@dataclass(frozen=True)
class BucketTriggerConfig:
    name: str
    prefix: str
    suffix: str


@dataclass(unsafe_hash=True)
class InstanceConfig:
    lambda_timeout: int = 240
    lambda_memory: int = 128
    env: Path = Path(DEFAULT_ENV_FILE)
    extra_layers: tuple = ()
    s3_access: tuple = ()
    managed_buckets: tuple = ()
    upload_triggers: Tuple[BucketTriggerConfig] = ()
    enable_api: bool = False

    def __post_init__(self):
        # ensure some keys are paths
        self.env = Path(self.env)

        # lists are not hashable, and Config must be hashable
        for key in ["extra_layers", "s3_access", "managed_buckets"]:
            setattr(self, key, tuple(getattr(self, key)))

        # Convert types
        self.upload_triggers = tuple(
            BucketTriggerConfig(*val) if isinstance(val, list) else val
            for val in self.upload_triggers
        )
