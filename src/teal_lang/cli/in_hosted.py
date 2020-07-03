"""Operate in the hosted Teal Cloud"""

from ..cloud import aws
from ..config import Config
from . import interface as ui


def deploy(args, config: Config):
    raise NotImplementedError

    python_zip = config.project.data_dir / "python.zip"
    teal_zip = config.project.data_dir / "teal.zip"
    config_json = config.project.data_dir / "config.json"

    with ui.spin(args, "Building packages...") as sp:
        deploy.package_python(config, python_zip)
        deploy.package_teal(config, teal_zip)
        deploy.package_config(Path(args["--config"]), config_json)
        sp.ok(ui.TICK)

    with ui.spin(args, "Uploading data"):
        # response = requests.post(TEAL_ENDPOINT + "/new_upload", project=project)
        # teal_uri = response["teal_uri"]
        # s3 upload everything
        deploy.upload_to_s3(teal_uri, teal_zip)
        deploy.upload_to_s3(python_uri, python_zip)
        sp.ok(ui.TICK)

    with ui.spin(args, f"Deploying {tag}"):
        # upload to bucket
        # requests.post(
        #     TEAL_ENDPOINT + "/deploy", project=project, tag=tag, s3_url=s3_url
        # )
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
