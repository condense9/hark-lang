"""Operate in the hosted Teal Cloud"""

import json
import logging
import os
import time
import zipfile
from pathlib import Path

from ..cloud import aws
from ..config import Config
from . import hosted_query as q
from . import interface as ui
from .utils import make_python_layer_zip

LOG = logging.getLogger(__name__)


def deploy(args, config: Config):
    """Deploy to Teal Cloud"""
    python_zip = config.project.data_dir / "python.zip"

    # 1. Build {python, teal, config} packages
    # 2. Compute the hashes
    with ui.spin(args, "Building source package") as sp:
        make_python_layer_zip(config, python_zip)
        sp.ok(ui.TICK)

    # 3. Request a new package with the hashes
    with ui.spin(args, "Checking for differences") as sp:
        instance = q.get_instance(config.project_id, config.instance.name)
        if not instance.ready:
            ui.exit_fail(f"Instance {config.instance.name} isn't ready yet.")
        python_hash = aws.hash_file(python_zip)
        teal_hash = aws.hash_file(config.project.teal_file)
        config_hash = aws.hash_file(config.config_file)
        package = q.new_package(instance.id, python_hash, teal_hash, config_hash)
        sp.ok(ui.TICK)

    # 4. Upload the files that have changed
    with ui.spin(args, "Uploading modified code") as sp:
        if package.new_python:
            _upload_to_s3(package.python_url, python_zip)
        if package.new_teal:
            _upload_to_s3(package.teal_url, config.project.teal_file)
        if package.new_config:
            _upload_to_s3(package.config_url, config.config_file)
        sp.ok(ui.TICK)

    # 5. Create a deployment
    with ui.spin(args, f"Deploying {config.instance.name}") as sp:
        deployment = q.new_deployment(instance.id, package.id)
        q.switch(instance.id, deployment.id)
        # TODO poll status until done
        start = time.time()

        while True:
            if time.time() - start > 120:
                ui.exit_fail("Deployment took too long - something didn't work :(")

            status = q.status(deployment.id)
            if status.active:
                break

            if status.started_deploy:
                info = ui.dim(f"started at {status.started_at}")
            else:
                info = ui.dim(f"waiting")

            sp.text = f"Deploying {config.instance.name}... {info}"

        sp.ok(ui.TICK)

    print(ui.good(f"\nDone. `teal invoke` to run main()."))


def invoke(args, config: Config, payload: dict) -> dict:
    raise NotImplementedError


def destroy(args, config: Config):
    raise NotImplementedError


def stdout(args, config: Config, session_id: str) -> dict:
    raise NotImplementedError


def events(args, config: Config, session_id: str) -> dict:
    raise NotImplementedError


def logs(args, config: Config, session_id: str) -> dict:
    raise NotImplementedError


## Helpers:


def _upload_to_s3(s3_url: str, filepath: Path):
    LOG.info(f"Uploading {filepath} to {s3_url}")
    client = aws.get_client("s3")
    bucket, key = aws.get_bucket_and_key(s3_url)
    aws.upload_if_necessary(client, bucket, key, filepath)
