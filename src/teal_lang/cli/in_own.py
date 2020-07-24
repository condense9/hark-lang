"""Operate in your own cloud"""
import json
import logging

from ..cloud import aws
from ..cloud.api import TealInstanceApi
from ..config import Config
from . import interface as ui
from .utils import get_layer_zip_path

LOG = logging.getLogger(__name__)


def _update_sp(prefix, sp):
    """Return a function to update spinner text with the current resource"""

    def update(resource):
        if type(resource) == type:
            item = ui.dim(resource.__name__ + "...")
        else:
            item = ui.dim(str(resource) + "...")
        sp.text = f"{prefix} {item}"

    return update


def deploy(config: Config, instance_api):
    layer_zip = get_layer_zip_path(config)

    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid,
        instance=config.instance,
        source_layer_hash=aws.hash_file(layer_zip),
        source_layer_file=layer_zip,
    )

    spin_msg = "Deploying infrastructure"
    with ui.spin(spin_msg) as sp:
        # this is idempotent
        aws.deploy(deploy_config, callback_start=_update_sp(spin_msg, sp))
        sp.text = spin_msg + ui.dim(f" Build data: {config.project.data_dir}/")
        sp.ok(ui.TICK)

    with ui.spin("Checking API") as sp:
        version = instance_api.version()
        sp.text += " Teal " + ui.dim(version)
        sp.ok(ui.TICK)

    with ui.spin(f"Deploying {config.project.teal_file}") as sp:
        # See teal_lang/executors/awslambda.py
        with open(config.project.teal_file) as f:
            content = f.read()

        instance_api.set_exe(content)
        sp.ok(ui.TICK)

    LOG.info(f"Uploaded {config.project.teal_file}")
    print(ui.good(f"\nDone. `teal invoke` to run main()."))


def destroy(config: Config):
    deploy_config = aws.DeployConfig(
        uuid=config.instance_uuid, instance=config.instance,
    )

    spin_msg = "Destroying infrastructure"
    with ui.spin(spin_msg) as sp:
        aws.destroy(deploy_config, callback_start=_update_sp(spin_msg, sp))
        sp.text = spin_msg
        sp.ok(ui.TICK)

    print(ui.good(f"\nDone. You can safely `rm -rf {config.project.data_dir}`."))
