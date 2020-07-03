"""Teal.

Usage:
  teal [options] info
  teal [options] asm FILE
  teal [options] ast [-o OUTPUT] FILE
  teal [options] deploy [--config CONFIG]
  teal [options] destroy [--config CONFIG]
  teal [options] invoke [--config CONFIG] [ARG...]
  teal [options] events [--config CONFIG] [--unified | --json] [SESSION_ID]
  teal [options] stdout [--config CONFIG] [--json] [SESSION_ID]
  teal [options] FILE [ARG...]
  teal --version
  teal --help

Commands:
  info     Show info about this Teal environment
  asm      Compile a file and print the bytecode listing.
  ast      Create a data flow graph (PNG).
  deploy   Deploy to the cloud.
  destroy  Remove cloud deployment.
  invoke   Invoke a teal function in the cloud.
  events   Get events for a session.
  stdout   Get session output.
  default  Run a Teal function locally.

Options:
  -h, --help      Show this screen.
  -q, --quiet     Be quiet.
  -v, --verbose   Be verbose.
  -V, --vverbose  Be very verbose.
  --version       Show version.
  --no-colours    Disable colours in CLI output.

  --endpoint URL  Teal Cloud endpoint (default: env.TEAL_ENDPOINT).

  -f FUNCTION, --fn=FUNCTION   Function to run      [default: main]
  -s MODE, --storage=MODE      memory | dynamodb    [default: memory]
  -c MODE, --concurrency=MODE  processes | threads  [default: threads]

  -o OUTPUT  Name of the output file

  --config CONFIG  Config file to use  [default: teal.toml]

  -u, --unified  Merge events into one table
  -j, --json     Print as json
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
from . import interface as ui
from . import utils
from .interface import (
    CROSS,
    TICK,
    bad,
    check,
    dim,
    exit_fail,
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

        try:
            config_file = Path(args["--config"])
            cfg = config.load(config_file=config_file)
        except config.ConfigError as exc:
            exit_fail(exc)

        return fn(args, cfg=cfg)

    return _wrapped


def _run(args):
    fn = args["--fn"]
    filename = args["FILE"]
    sys.path.append(".")

    fn_args = args["ARG"]

    LOG.info(f"Running `{fn}` in {filename} ({len(fn_args)} args)...")

    # Try to find a timeout for the task. NOTE: we use the "lambda" timeout even
    # for local invocations. Maybe there should be a more general timeout
    config_file = Path(args["--config"])
    try:
        cfg = config.load(config_file=config_file)
        timeout = cfg.instance.lambda_timeout
    except config.ConfigError:
        timeout = 10

    if args["--storage"] == "memory":
        if args["--concurrency"] == "processes":
            exit_fail("Can't use processes with in-memory storage")

        from ..run.local import run_local

        result = run_local(filename, fn, fn_args, timeout)

    elif args["--storage"] == "dynamodb":
        from ..run.dynamodb import run_ddb_local, run_ddb_processes

        if args["--concurrency"] == "processes":
            result = run_ddb_processes(filename, fn, fn_args, timeout)
        else:
            result = run_ddb_local(filename, fn, fn_args, timeout)

    else:
        exit_fail("Bad storage type: " + str(args["--storage"]))

    if result:
        print(result)


def _ast(args):
    fn = args["--fn"]
    filename = Path(args["FILE"])

    if args["-o"]:
        dest_png = args["-o"]
    else:
        dest_png = f"{filename.stem}_{fn}.png"
    raise NotImplementedError


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
    if cfg.endpoint and not cfg.instance_uuid:
        if not cfg.project_id:
            from . import hosted_query

            print("No project configured, retrieving your projects...")
            projects = hosted_query.list_projects()
            options = [p.name for p in projects]
            choice = ui.select("Which project would you like?", options)
            if choice:
                project_id = next(p.id for p in projects if p.name == choice)
                config.set_project_id(cfg, project_id)
                cfg.project_id = project_id

        if cfg.project_id:
            return do_in_hosted

    if not cfg.instance_uuid:
        if can_create_uuid and check(
            "No Teal instance found - would you like to create one?"
        ):
            cfg.instance_uuid = config.new_instance_uuid(cfg)
        else:
            exit_fail("No instance UUID or endpoint configured.")

    return do_in_own


@timed
@need_cfg
def _deploy(args, cfg):
    from . import in_own, in_hosted

    # TODO prompt when it looks like this is a new instance. Make sure! Need an
    # AWS method (e.g. check whether the first/last resources exist)

    deployer = _local_or_cloud(
        cfg, in_own.deploy, in_hosted.deploy, can_create_uuid=True
    )
    deployer(args, cfg)


@timed
@need_cfg
def _destroy(args, cfg):
    from . import in_own, in_hosted

    destroyer = _local_or_cloud(cfg, in_own.destroy, in_hosted.destroy)
    destroyer(args, cfg)


@timed
@need_cfg
def _invoke(args, cfg):
    from . import in_own, in_hosted

    function = args.get("--fn", "main")
    payload = {
        TEAL_CLI_VERSION_KEY: __version__,
        "function": function,
        "args": args["ARG"],
        "timeout": cfg.instance.lambda_timeout - 3,  # FIXME why is -3 needed?
    }

    with spin(args, str(primary(f"{function}(...)"))) as sp:
        invoker = _local_or_cloud(cfg, in_own.invoke, in_hosted.invoke)
        data = invoker(args, cfg, payload)
        sp.text += " " + dim(data["session_id"])

        if data["broken"]:
            sp.fail(CROSS)
        else:
            sp.ok(TICK)

    utils.save_last_session_id(cfg, data["session_id"])

    # Print the standard output and result immediately
    if data["finished"]:
        if not args["--quiet"]:
            _stdout(args)
            print(dim("\n=>"))
        print(data["result"])


@timed
@need_cfg
def _events(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)

    if sid is None:
        exit_fail("No session ID specified, and no previous session found.")

    invoker = _local_or_cloud(cfg, in_own.events, in_hosted.events)

    if args["--json"]:
        # Don't show the spinner in JSON mode
        data = invoker(args, cfg, sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(args, f"Getting events {dim(sid)}"):
            data = invoker(args, cfg, sid)
        if args["--unified"]:
            ui.print_events_unified(data)
        else:
            ui.print_events_by_machine(data)


@need_cfg
def _stdout(args, cfg):
    from . import in_own, in_hosted

    sid = utils.get_session_id(args, cfg)

    if sid is None:
        exit_fail("No session ID specified, and no previous session found.")

    invoker = _local_or_cloud(cfg, in_own.stdout, in_hosted.stdout)
    if args["--json"]:
        data = invoker(args, cfg, sid)
        print(json.dumps(data, indent=2))
    else:
        with spin(args, f"Getting stdout {dim(sid)}") as sp:
            data = invoker(args, cfg, sid)
            sp.ok(TICK)
        ui.print_outputs(data)


@timed
def _info(args):
    # API URL
    # deployment ID
    # deployed teal version
    # last session ID
    # links to console items?
    raise NotImplementedError


def main():
    args = docopt(__doc__, version=__version__)
    init(args)
    LOG.debug("CLI args: %s", args)
    if not args["--quiet"]:
        print("")  # Space in the CLI

    if args["ast"]:
        _ast(args)
    elif args["info"]:
        _info(args)
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
        print(bad("Invalid command line.\n"))
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
