"""CLI related utilities"""
import logging
from pathlib import Path
from typing import Union

from ..config import Config, load
from .interface import exit_fail

LOG = logging.getLogger(__name__)
LAST_SESSION_FILENAME = "last_session_id.txt"


def save_last_session_id(cfg: Config, session_id: str):
    last_session_file = cfg.service.data_dir / LAST_SESSION_FILENAME
    with open(last_session_file, "w") as f:
        f.write(session_id)
        LOG.info("Session ID: %s (saved in %s)", session_id, last_session_file)


def load_last_session_id(cfg: Config) -> Union[str, None]:
    """Get the last session ID"""
    last_session_file = cfg.service.data_dir / LAST_SESSION_FILENAME
    if not last_session_file.exists():
        return None
    with open(last_session_file, "r") as f:
        return f.read()


def get_session_id(args):
    session_id = args["SESSION_ID"]
    if session_id is None:
        cfg = load(config_file=Path(args["--config"]), require_dep_id=True)
        session_id = load_last_session_id(cfg)
    if session_id is None:
        exit_fail("No session ID specified, and no previous session found.")
    return session_id
