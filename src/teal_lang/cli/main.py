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

TEAL_CLI_VERSION_KEY = "teal_ver"


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


def _local_or_cloud(cfg, do_in_own, do_in_hosted, can_create_uuid=False):
    """Helper - do something either in your cloud or the hosted Teal Cloud"""
    # Self-managed
    if cfg.instance_uuid:
        print(dim(f"Target: Self-hosted instance {cfg.instance_uuid}.\n"))
        return do_in_own

    # Managed by Teal Cloud
    elif cfg.project_id:
        m = f"Target: Teal Cloud project #{cfg.project_id}, instance {cfg.instance_name}.\n"
        print(dim(m))
        return do_in_hosted

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

    options = [TEAL_CLOUD, USE_EXISTING]
    if can_create_uuid:
        options += [CREATE_NEW]

    choice = ui.select("What would you like to do?", options)

    if choice is None:
        sys.exit(1)

    elif choice == CREATE_NEW:
        cfg.instance_uuid = config.new_instance_uuid(cfg)
        return do_in_own

    elif choice == USE_EXISTING:
        # TODO scan account and look for likely UUIDs...
        value = ui.get_input("Instance UUID?")
        if not value:
            sys.exit(1)
        cfg.instance_uuid = value
        config.save_instance_uuid(cfg, value)
        return do_in_own

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
        return do_in_hosted

    else:
        assert False, "Not reachable"


@need_cfg
def _deploy(args, cfg):
    from . import in_own, in_hosted

    deployer = _local_or_cloud(
        cfg, in_own.deploy, in_hosted.deploy, can_create_uuid=True
    )
    deployer(cfg)


@need_cfg
def _destroy(args, cfg):
    from . import in_own, in_hosted

    destroyer = _local_or_cloud(cfg, in_own.destroy, in_hosted.destroy)
    destroyer(cfg)


@need_cfg
def _invoke(args, cfg):
    from . import in_own, in_hosted

    function = args["--function"]
    timeout = cfg.instance.lambda_timeout - 3  # FIXME why is -3 needed?
    method = _local_or_cloud(cfg, in_own.invoke, in_hosted.invoke)

    with spin(str(primary(f"{function}(...)"))) as sp:
        data = method(cfg, function, args["ARG"], timeout, not args["--async"])
        sp.text += " " + dim(data["session_id"])

        if data["broken"]:
            sp.fail(CROSS)
        else:
            sp.ok(TICK)

    utils.save_last_session_id(cfg, data["session_id"])

    # Print the standard output and result immediately
    if not args["--quiet"]:
        _stdout(args)
        print(dim("\n=>"))
    print(data["result"])
    if not data["finished"]:
        print("(Continuing async...)")


@need_cfg
def _events(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)
    method = _local_or_cloud(cfg, in_own.events, in_hosted.events)

    if args["--json"]:
        # Don't show the spinner in JSON mode
        data = method(args, cfg, sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(f"Getting events {dim(sid)}"):
            data = method(args, cfg, sid)
        if args["--unified"]:
            ui.print_events_unified(data)
        else:
            ui.print_events_by_machine(data)


@need_cfg
def _stdout(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)
    method = _local_or_cloud(cfg, in_own.stdout, in_hosted.stdout)

    if args["--json"]:
        data = method(args, cfg, sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(f"Getting stdout {dim(sid)}") as sp:
            data = method(args, cfg, sid)
            sp.ok(TICK)
        ui.print_outputs(data)


@need_cfg
def _info(args, cfg):
    # API URL
    # deployment ID
    # deployed teal version
    # last session ID
    # links to console items?
    raise NotImplementedError


def _init(args):
    config.create_skeleton()
    print("\n" + TICK + good(f" Created ./{config.DEFAULT_CONFIG_FILEPATH}\n"))


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
