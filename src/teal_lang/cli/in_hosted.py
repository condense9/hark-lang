"""Operate in the hosted Teal Cloud"""

import json
import logging
import os
import time
import zipfile
from pathlib import Path

from ..cloud import aws
from ..cloud.api import TealInstanceApi
from ..config import Config
from ..exceptions import UserResolvableError
from . import hosted_query as q
from . import interface as ui
from .utils import make_python_layer_zip

LOG = logging.getLogger(__name__)


class TealCloudTookTooLong(UserResolvableError):
    """Something took too long in Teal Cloud"""

    def __init__(self, msg):
        super().__init__(msg, "Check Teal Cloud for issues, and try again.")


def get_instance_state(cfg):
    """Get instance details from Teal Cloud"""
    with ui.spin("Getting project and instance details ") as sp:
        instance = q.get_instance(cfg.project_id, cfg.instance_name)
        if not instance:
            raise UserResolvableError(
                f"Can't find an instance called {cfg.instance_name}.",
                f"Is the project ID ({cfg.project_id}) correct?",
            )
        sp.text += ui.dim(f"{instance.project.name} :: {instance.uuid} ")
        sp.ok(ui.TICK)
    return instance


def deploy(config: Config, instance_api):
    """Deploy to Teal Cloud"""
    instance = instance_api.hosted_instance_state

    if not instance.ready:
        raise UserResolvableError(
            f"Instance {config.instance_name} isn't ready for deployments.",
            "Check Teal Cloud and try again.",
        )

    with ui.spin("Checking API") as sp:
        version = instance_api.version()
        sp.text += " Teal " + ui.dim(version)
        sp.ok(ui.TICK)

    # 1. Build {python, teal, config} packages
    # 2. Compute the hashes
    with ui.spin("Building source package") as sp:
        python_zip = config.project.data_dir / "python.zip"
        make_python_layer_zip(config, python_zip)
        sp.ok(ui.TICK)

    # 3. Request a new package with the hashes
    with ui.spin("Checking for differences ") as sp:
        python_hash = aws.hash_file(python_zip)
        teal_hash = aws.hash_file(config.project.teal_file)
        config_hash = aws.hash_file(config.config_file)
        package = q.new_package(instance.id, python_hash, teal_hash, config_hash)
        changed = {
            "Python": package.new_python,
            "Teal": package.new_teal,
            "Config": package.new_config,
        }
        sp.text += ui.dim(
            ", ".join(
                thing + ": " + ("Changed" if new else "Same")
                for thing, new in changed.items()
            )
        )
        sp.ok(ui.TICK)

    # 4. Upload the files that have changed
    if package.new_python:
        with ui.spin("Uploading new Python ") as sp:
            instance_api.upload_file(package.python_url, python_zip)
            sp.text += ui.dim(python_hash)
            sp.ok(ui.TICK)
    if package.new_teal:
        with ui.spin("Uploading new Teal ") as sp:
            instance_api.upload_file(package.teal_url, config.project.teal_file)
            sp.text += ui.dim(teal_hash)
            sp.ok(ui.TICK)
    if package.new_config:
        with ui.spin("Updating configuration ") as sp:
            instance_api.upload_file(package.config_url, config.config_file)
            sp.text += ui.dim(config_hash)
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


def destroy(config: Config, instance_api):
    with ui.spin(f"Destroying instance '{config.instance_name}'") as sp:
        instance = instance_api.hosted_instance_state
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
