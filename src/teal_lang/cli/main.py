"""Teal.

Usage:
  teal [options] info
  teal [options] init
  teal [options] asm FILE
  teal [options] deploy
  teal [options] destroy
  teal [options] invoke [-f FUNCTION] [--async] [ARG...]
  teal [options] events [--unified | --json] [SESSION_ID]
  teal [options] stdout [--json] [SESSION_ID]
  teal [options] FILE [-f FUNCTION] [-s MODE] [-c MODE] [ARG...]
  teal --version
  teal -h | --help

Commands:
  info     Show info about this Teal environment
  asm      Compile a file and print the bytecode listing.
  deploy   Deploy to the cloud.
  destroy  Remove cloud deployment.
  invoke   Invoke a teal function in the cloud.
  events   Get events for a session.
  stdout   Get session output.
  default  Run a Teal function locally.

Options:
  --version       Show version.
  -h, --help      Show this screen.
  -q, --quiet     Be quiet.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --no-colours    Disable colours in CLI output.

  --config=CONFIG  Config file to use  [default: teal.toml]

  -f FUNCTION, --function=FUNCTION  Target function      [default: main]
  -s MODE, --storage=MODE           memory | dynamodb    [default: memory]
  -c MODE, --concurrency=MODE       processes | threads  [default: threads]

  -u, --unified  Merge events into one table
  -j, --json     Print as json

Teal cloud options:
  --project=ID  Teal Cloud Project ID
  --name=NAME   Teal Cloud instance name  [default: dev]
  --uuid=UUID   Self-hosted instance UUID
"""

# http://try.docopt.org/
#
# - pyfiglet https://github.com/pwaller/pyfiglet
# - typer? https://typer.tiangolo.com/

import json
import logging
import subprocess
import sys
import time
from functools import wraps
from pathlib import Path

from docopt import docopt

from .. import __version__, config
from ..exceptions import UserResolvableError, UnexpectedError
from ..cloud.api import TealInstanceApi
from . import interface as ui
from . import utils
from .interface import (
    CROSS,
    TICK,
    bad,
    check,
    dim,
    exit_problem,
    exit_bug,
    good,
    init,
    neutral,
    primary,
    spin,
)

LOG = logging.getLogger(__name__)

ENABLE_TEAL_CLOUD = False  # for now...


def timed(fn):
    """Time execution of fn and print it"""

    @wraps(fn)
    def _wrapped(args, **kwargs):
        start = time.time()
        fn(args, **kwargs)
        end = time.time()
        if not args["--quiet"]:
            sys.stderr.write(str(dim(f"\n-- {int(end-start)}s\n")))

    return _wrapped


def need_cfg(fn):
    """Exec fn with config, requiring a deployment ID"""

    @wraps(fn)
    def _wrapped(args):
        cfg = config.load(args)
        return fn(args, cfg=cfg)

    return _wrapped


def _run(args):
    fn = args["--function"]
    filename = args["FILE"]
    sys.path.append(".")

    fn_args = args["ARG"]

    LOG.info(f"Running `{fn}` in {filename} ({len(fn_args)} args)...")

    # Try to find a timeout for the task. NOTE: we use the "lambda" timeout even
    # for local invocations. Maybe there should be a more general timeout
    try:
        cfg = config.load(args)
        timeout = cfg.instance.lambda_timeout
    except config.ConfigError:
        # Don't actually need teal.toml to run stuff locally, so here's a
        # default. Maybe it should be None.
        timeout = 60

    supported_storages = ["memory", "dynamodb"]

    if args["--storage"] not in supported_storages:
        exit_problem(
            "Bad storage type: " + str(args["--storage"]),
            f"Supported types: {supported_storages}",
        )

    if args["--storage"] == "memory":
        if args["--concurrency"] == "processes":
            exit_problem(
                "Can't use processes with in-memory storage",
                "Processes can only be used with a thread-safe memory store, like dynamodb",
            )

        from ..run.local import run_local

        result = run_local(filename, fn, fn_args, timeout)

    elif args["--storage"] == "dynamodb":
        from ..run.dynamodb import run_ddb_local, run_ddb_processes

        if args["--concurrency"] == "processes":
            result = run_ddb_processes(filename, fn, fn_args, timeout)
        else:
            result = run_ddb_local(filename, fn, fn_args, timeout)

    else:
        raise ValueError(args["--storage"])

    if result:
        print(result)


def _asm(args):
    """Compile a file and print the assembly"""
    from ..load import compile_file

    exe = compile_file(Path(args["FILE"]))
    print(neutral("\nBYTECODE:"))
    exe.listing()
    print(neutral("\nBINDINGS:\n"))
    exe.bindings_table()
    print()


def _get_instance_api(cfg, can_create_new=False) -> TealInstanceApi:
    """Get the Teal Instance API, depending on user configuration"""
    # Self-managed
    if cfg.instance_uuid:
        ui.info(dim(f"Target: Self-hosted instance {cfg.instance_uuid}\n"))
        return TealInstanceApi(cfg)

    from .in_hosted import get_instance_state

    # Managed by Teal Cloud
    if cfg.project_id:
        m = f"Target: Teal Cloud project #{cfg.project_id}, instance {cfg.instance_name}.\n"
        ui.info(dim(m))

        instance = get_instance_state(cfg)
        cfg.instance_uuid = instance.uuid
        return TealInstanceApi(cfg, hosted_instance_state=instance)

    # Neither. Ask what the user wants
    print(
        ui.primary(
            "\n"
            "No deployment target found - checked command line flags and config files."
            "\n"
        )
    )
    CREATE_NEW = "Create a new self-hosted instance (using local AWS credentials)."
    USE_EXISTING = "Use an existing self hosted instance."
    TEAL_CLOUD = "Choose a project in Teal Cloud."
    CANCEL = "Cancel."

    options = [USE_EXISTING, CANCEL]
    if can_create_new:
        options = [CREATE_NEW] + options

    if ENABLE_TEAL_CLOUD:
        options = [TEAL_CLOUD] + options

    choice = ui.select("What would you like to do?", options)

    if choice is None or choice == CANCEL:
        sys.exit(1)

    elif choice == CREATE_NEW:
        cfg.instance_uuid = config.new_instance_uuid(cfg)
        return TealInstanceApi(cfg)

    elif choice == USE_EXISTING:
        # TODO scan account and look for likely UUIDs...
        value = ui.get_input("Instance UUID?")
        if not value:
            sys.exit(1)
        cfg.instance_uuid = value
        config.save_instance_uuid(cfg, value)
        return TealInstanceApi(cfg)

    elif choice == TEAL_CLOUD:
        from . import hosted_query

        with ui.spin("Retrieving your projects..."):
            projects = hosted_query.list_projects()

        options = [p.name for p in projects]
        choice = ui.select("Which project would you like?", options)
        if not choice:
            sys.exit(1)
        project_id = next(p.id for p in projects if p.name == choice)
        cfg.project_id = project_id
        config.save_project_id(cfg, project_id)

        instance = get_instance_state(cfg)
        cfg.instance_uuid = instance.uuid
        return TealInstanceApi(cfg, hosted_instance_state=instance)

    else:
        assert False, "Not reachable"


@need_cfg
def _deploy(args, cfg):
    from . import in_own, in_hosted

    api = _get_instance_api(cfg, can_create_new=True)

    if api.self_hosted:
        in_own.deploy(cfg, api)
    else:
        in_hosted.deploy(cfg, api)


@need_cfg
def _destroy(args, cfg):
    from . import in_own, in_hosted

    api = _get_instance_api(cfg)

    if api.self_hosted:
        in_own.destroy(cfg)
    else:
        in_hosted.destroy(cfg, api)


@need_cfg
def _invoke(args, cfg):
    from . import in_own, in_hosted

    teal_fn = args["--function"]
    teal_args = args["ARG"]
    timeout = cfg.instance.lambda_timeout - 3  # FIXME why is -3 needed?
    wait_for_finish = not args["--async"]

    api = _get_instance_api(cfg)

    with spin(str(primary(f"{teal_fn}(...)"))) as sp:
        session = api.invoke(teal_fn, teal_args, timeout, wait_for_finish)

        sp.text += " " + dim(session.session_id)
        utils.save_last_session_id(cfg, session.session_id)

        if session.broken:
            sp.fail(CROSS)
            sys.exit(1)
        else:
            sp.ok(TICK)

    # Print the standard output and result immediately
    if not args["--quiet"]:
        with spin("Getting stdout...") as sp:
            data = api.get_stdout(session.session_id)
            sp.ok(TICK)
        ui.print_outputs(data)
        print(dim("\n=>"))
    print(session.result)
    if not session.finished:
        print("(Continuing async...)")


@need_cfg
def _events(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)
    api = _get_instance_api(cfg)

    if args["--json"]:
        # Don't show the spinner in JSON mode
        data = api.get_events(sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(f"Getting events {dim(sid)}"):
            data = api.get_events(sid)
        if args["--unified"]:
            ui.print_events_unified(data)
        else:
            ui.print_events_by_machine(data)


@need_cfg
def _stdout(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)
    api = _get_instance_api(cfg)

    if args["--json"]:
        data = api.get_stdout(sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(f"Getting stdout {dim(sid)}") as sp:
            data = api.get_stdout(sid)
            sp.ok(TICK)
        ui.print_outputs(data)


@need_cfg
def _info(args, cfg):
    api = _get_instance_api(cfg)
    version = api.version()
    print()

    def p(k, v):
        print(k + " " + ui.primary(v))

    p("Target:", "self-hosted" if api.self_hosted else "Teal Cloud")

    if not api.self_hosted:
        p("Project:", api.hosted_instance_state.project.name)
        p("Instance:", cfg.instance_name)

    p("Instance UUID:", cfg.instance_uuid)

    p("Deployed?", "Yes" if version else "No")

    if version:
        p("Deployed version", version)

    sid = utils.load_last_session_id(cfg)
    if version and sid:
        p("Last session ID:", sid)

    endpoint = api.get_api_endpoint()
    if endpoint:
        p("API Endpoint:", endpoint)

    # TODO:
    # deployment ID
    # last session ID
    # links to console items?
    # other infrastructure details?
    print()


def _init(args):
    config.create_skeleton()
    cfg = config.load(args)
    new_src, new_teal = utils.init_src(cfg)
    print("\n" + TICK + " Created " + good(config.DEFAULT_CONFIG_FILEPATH))
    if new_src:
        print(TICK + " Created " + good(new_src))
    if new_teal:
        print(TICK + " Created " + good(new_teal))

    print("\nDone. Ready for `teal deploy`.")


@timed
def dispatch(args):
    if args["info"]:
        _info(args)
    elif args["init"]:
        _init(args)
    elif args["asm"]:
        _asm(args)
    elif args["deploy"]:
        _deploy(args)
    elif args["destroy"]:
        _destroy(args)
    elif args["invoke"]:
        _invoke(args)
    elif args["events"]:
        _events(args)
    elif args["stdout"]:
        _stdout(args)
    elif args["FILE"] and args["FILE"].endswith(".tl"):
        _run(args)
    else:
        exit_problem("Invalid command line.", __doc__)


def main():
    args = docopt(__doc__, version=__version__)
    init(args)
    LOG.debug("CLI args: %s", args)

    try:
        dispatch(args)
    except UserResolvableError as exc:
        exit_problem(exc.msg, exc.suggested_fix)
    except UnexpectedError as exc:
        exit_bug(str(exc))


if __name__ == "__main__":
    main()
