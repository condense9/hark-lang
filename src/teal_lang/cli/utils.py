"""CLI related utilities"""
import logging
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Union

import deterministic_zip as dz

from ..config import Config, load
from . import interface as ui

LOG = logging.getLogger(__name__)
LAST_SESSION_FILENAME = "last_session_id.txt"


def save_last_session_id(cfg: Config, session_id: str):
    last_session_file = cfg.project.data_dir / LAST_SESSION_FILENAME
    with open(last_session_file, "w") as f:
        f.write(session_id)
        LOG.info("Session ID: %s (saved in %s)", session_id, last_session_file)


def load_last_session_id(cfg: Config) -> Union[str, None]:
    """Get the last session ID"""
    last_session_file = cfg.project.data_dir / LAST_SESSION_FILENAME
    if not last_session_file.exists():
        return None
    with open(last_session_file, "r") as f:
        return f.read()


def get_session_id(args, cfg: Config, required=True):
    session_id = args["SESSION_ID"]
    if session_id is None:
        session_id = load_last_session_id(cfg)
    if required and session_id is None:
        ui.exit_problem(
            "No session ID specified, and no previous session found."
            "Either pass a --session parameter, or echo $SESSION > "
            f"{cfg.project.data_dir}/{LAST_SESSION_FILENAME}"
        )
    return session_id


def zip_dir(dirname: Path, dest: Path, deterministic=True):
    """Zip a directory"""
    # https://github.com/bboe/deterministic_zip/blob/master/deterministic_zip/__init__.py
    with zipfile.ZipFile(dest, "w") as zip_file:
        dz.add_directory(zip_file, dirname, dirname.name)


def make_python_layer_zip(config: Config, dest: Path):
    """Create the python code layer Zip, saving it in dest"""
    root = Path(__file__).parents[3]

    if not config.project.python_src.exists():
        ui.exit_problem(
            f"Python source directory ({config.project.python_src}) not found",
            "Is your configuration (in {config.config_file}) correct?",
        )

    LOG.info(f"Building Source Layer package in {dest}...")
    workdir = config.project.data_dir / "source_build" / "python"
    os.makedirs(workdir, exist_ok=True)

    # User source
    shutil.copytree(
        config.project.python_src,
        workdir / config.project.python_src.name,
        dirs_exist_ok=True,
    )

    # Pip requirements if they exist
    reqs_file = config.project.python_requirements
    if reqs_file.exists():
        LOG.info(
            f"Installing pip packages from {config.project.python_requirements}..."
        )
        subprocess.check_output(
            ["pip", "install", "-q", "--target", workdir, "-r", reqs_file]
        )

    # Make sure the zip is not empty
    with open(workdir / ".packaged_by_teal.txt", "w") as f:
        f.write("Packed by Teal :)")

    zip_dir(workdir, dest)
