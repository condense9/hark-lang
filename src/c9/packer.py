"""Python File -> C9 Executable File"""

import importlib
import logging
import os
import tempfile
from os.path import basename, dirname, join, normpath, splitext
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
        if path.endswith(".py") and os.path.isfile(path):
            module_name = splitext(basename(path))[0]
            spec = importlib.util.spec_from_file_location(module_name, path)
            m = spec.loader.load_module()
        else:
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

    executable = compiler.link(compiler.compile_all(handler_fn), exe_name)
    c9e.dump(executable, dest)


def file_module(fname):
    if not fname.endswith(".py"):
        raise ValueError
    return fname.split(".py")[0].replace("/", ".")


def pack_deployment(
    service_file: str,
    attr: str,
    dest: str,
    include: list,
    include_service_file_dir: bool,
):
    """Pack a service for deployment """
    # a service file must be part of a module
    m = _import_module(file_module(service_file))
    service = getattr(m, attr)

    if not isinstance(service, Service):
        raise PackerError(f"Not a Service: '{attr}' in {service_file}")

    with tempfile.TemporaryDirectory() as build_d:

        lambda_dirname = "lambda_code"
        pack_lambda_deployment(join(build_d, lambda_dirname), service, service_file)
        pack_iac(build_d, lambda_dirname, service)

        # zip_from_dir should probably be moved to a shared utils module:
        c9e.zip_from_dir(build_d, dest)


def pack_iac(build_d: str, lambda_dirname, service: Service):
    handlers = [h[1] for h in service.handlers]  # (name, handler) tuple
    resources = compiler.get_resources_set(handlers)
    state = SynthState(resources, [], [], lambda_dirname)

    for synth in service.pipeline:
        state = synth(state)

    if state.resources:
        warnings.warn(f"Some resources were not synthesised! {state.resources}")

    state.gen_iac(build_d)


def pack_lambda_deployment(build_d: str, service: Service, service_file):
    """Build the lambda source component of the deploy object"""

    # --> C9 Executables
    os.makedirs(join(build_d, EXE_PATH))
    for name, handler in service.handlers:
        executable = compiler.link(compiler.compile_all(handler), name)
        exe_dest = join(build_d, EXE_PATH, name + "." + c9e.FILE_EXT)
        c9e.dump(executable, exe_dest)

    # --> Python source/libs for Foreign calls
    os.makedirs(join(build_d, SRC_PATH))
    for include in service.include:
        root = dirname(service_file)
        full_path = join(root, include)
        if os.path.isfile(include):
            copy(full_path, join(build_d, SRC_PATH, basename(include)))
        else:
            copytree(full_path, join(build_d, SRC_PATH, basename(normpath(include))))
