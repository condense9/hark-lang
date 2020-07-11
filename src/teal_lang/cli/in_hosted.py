"""Operate in the hosted Teal Cloud"""

import json
import logging
import os
import time
import zipfile
from pathlib import Path

from ..cloud import aws
from ..config import Config
from ..exceptions import UserResolvableError
from . import hosted_query as q
from . import interface as ui
from .utils import make_python_layer_zip

LOG = logging.getLogger(__name__)


class TealCloudTookTooLong(UserResolvableError):
    """Something took too long in Teal Cloud"""

    def __init__(self, msg):
        super().__init__("Check Teal Cloud for issues, and try again.")


def deploy(args, config: Config):
    """Deploy to Teal Cloud"""

    with ui.spin("Getting project and instance details ") as sp:
        try:
            instance = q.get_instance(config.project_id, config.instance_name)
        except IndexError:
            raise UserResolvableError(
                f"Can't find an instance called {config.instance_name}.",
                f"Is the project ID ({config.project_id}) correct?",
            )
        sp.text += ui.dim(f"{instance.project.name} :: {instance.uuid} ")
        sp.ok(ui.TICK)

    # 1. Build {python, teal, config} packages
    # 2. Compute the hashes
    with ui.spin("Building source package") as sp:
        python_zip = config.project.data_dir / "python.zip"
        make_python_layer_zip(config, python_zip)
        sp.ok(ui.TICK)

    # 3. Request a new package with the hashes
    with ui.spin("Checking for differences") as sp:
        if not instance.ready:
            raise UserResolvableError(
                f"Instance {config.instance_name} isn't ready yet.",
                "Please wait a few minutes and try again.",
            )
        python_hash = aws.hash_file(python_zip)
        teal_hash = aws.hash_file(config.project.teal_file)
        config_hash = aws.hash_file(config.config_file)
        package = q.new_package(instance.id, python_hash, teal_hash, config_hash)
        sp.ok(ui.TICK)

    # 4. Upload the files that have changed
    if package.new_python:
        with ui.spin("Uploading new Python") as sp:
            _upload_to_s3(package.python_url, python_zip)
            sp.ok(ui.TICK)
    if package.new_teal:
        with ui.spin("Uploading new Teal") as sp:
            _upload_to_s3(package.teal_url, config.project.teal_file)
            sp.ok(ui.TICK)
    if package.new_config:
        with ui.spin("Updating configuration") as sp:
            _upload_to_s3(package.config_url, config.config_file)
            sp.ok(ui.TICK)

    # 5. Create a deployment
    with ui.spin(f"Deploying {config.instance_name}") as sp:
        deployment = q.new_deployment(instance.id, package.id)
        q.switch(instance.id, deployment.id)

        start = time.time()
        while True:
            if time.time() - start > 120:
                raise TealCloudTookTooLong("Waiting for deployment to complete")

            status = q.status(deployment.id)
            if status.active:
                break

            if status.started_deploy:
                info = ui.dim(f"started at {status.started_at}")
            else:
                info = ui.dim(f"waiting")

            sp.text = f"Deploying {config.instance_name}... {info}"
            time.sleep(0.5)

        sp.ok(ui.TICK)

    print(ui.good(f"\nDone. `teal invoke` to run main()."))


def destroy(args, config: Config):
    with ui.spin(f"Destroying {config.instance_name}") as sp:
        instance = q.get_instance(config.project_id, config.instance_name)
        q.destroy(instance.id)

        # And poll
        start = time.time()
        while True:
            if time.time() - start > 120:
                raise TealCloudTookTooLong("Waiting for destroy to complete")

            ready = q.is_instance_ready(instance.id)
            if not ready:
                break  # Done

            time.sleep(0.5)

        sp.ok(ui.TICK)


def invoke(config: Config, function, args, timeout) -> dict:
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
