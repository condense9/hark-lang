"""Python File -> C9 Executable File"""

import importlib
import logging
import os
import tempfile
from os.path import basename, dirname, join, normpath, splitext
import sys
from shutil import copy, copytree

from . import compiler
from .lang import Func
from .machine import c9e
from .service import Service
from .synthesiser.synthstate import SynthState

SRC_PATH = "src"
EXE_PATH = "exe"


class PackerError(Exception):
    """Error packing a handler or service"""


# https://pymotw.com/3/importlib/
def _import_module(path):
    logging.info(f"importing {path}")
    try:
        # UGLYyyyy
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
        m = importlib.import_module(path)
    except Exception as e:
        raise PackerError(f"Could not import {path}") from e
    return m


def pack_handler(handler_file: str, handler_attr: str, dest: str):
    """Try to import handler from"""
    m = _import_module(handler_file)
    exe_name = m.__name__ if handler_attr == "main" else handler_attr
    handler_fn = getattr(m, handler_attr)

    if not isinstance(handler_fn, Func):
        raise PackerError(f"Not a Func: '{handler_attr}' in {handler_file}")

    try:
        executable = compiler.link(compiler.compile_all(handler_fn), exe_name)
        c9e.dump(executable, dest)
    except Exception as e:
        raise PackerError from e


def pack_deployment(
    service_file: str, attr: str, build_d: str,
):
    """Pack a service for deployment """
    m = _import_module(service_file)
    service = getattr(m, attr)

    if not isinstance(service, Service):
        raise PackerError(f"Not a Service: '{attr}' in {service_file}")

    try:
        lambda_dirname = "lambda_code"
        pack_lambda_deployment(join(build_d, lambda_dirname), service, service_file)
        pack_iac(build_d, lambda_dirname, service)
    except Exception as e:
        raise PackerError from e


def pack_iac(build_d: str, lambda_dirname, service: Service):
    handlers = [h[1] for h in service.handlers]  # (name, handler) tuple
    resources = compiler.get_resources_set(handlers)
    state = SynthState(service.name, resources, [], [], lambda_dirname)

    print("Resources:", resources)
    for synth in service.pipeline:
        state = synth(state)

    if state.resources:
        warnings.warn(f"Some resources were not synthesised! {state.resources}")

    print("IAC:", state.iac)
    state.gen_iac(build_d)


def pack_lambda_deployment(build_d: str, service: Service, service_file):
    """Build the lambda source component of the deploy object"""

    # --> C9 Executables
    os.makedirs(join(build_d, EXE_PATH), exist_ok=True)
    for name, handler in service.handlers:
        executable = compiler.link(
            compiler.compile_all(handler), name, entrypoint_fn=handler.label
        )
        exe_dest = join(build_d, EXE_PATH, name + "." + c9e.FILE_EXT)
        c9e.dump(executable, exe_dest)

    with open(join(build_d, "main.py"), "w") as f:
        f.write(LAMBDA_MAIN)

    # --> Python source/libs for Foreign calls
    os.makedirs(join(build_d, SRC_PATH), exist_ok=True)
    root = dirname(service_file)
    for include in service.include:
        full_path = join(root, include)
        if os.path.isfile(include):
            copy(full_path, join(build_d, SRC_PATH, basename(include)))
        else:
            copytree(
                full_path,
                join(build_d, SRC_PATH, basename(normpath(include))),
                dirs_exist_ok=True,
            )


LAMBDA_MAIN = f"""
import sys

sys.path.append("{SRC_PATH}")

import c9.controllers.ddb
import c9.executors.awslambda

def c9_handler(event, context):
    run_method = c9.controllers.ddb.run_existing
    return c9.executors.awslambda.handle_existing(run_method, event, context)

def event_handler(event, context):
    run_method = c9.controllers.ddb.run
    return c9.executors.awslambda.handle_new(run_method, event, context)
"""
