"""Python File -> C9 Executable File"""

import importlib
import tempfile
import os
import logging
from os.path import basename, dirname, join, splitext, normpath
from shutil import copy, copytree

from . import compiler
from .machine import c9e
from .service import Service
from .lang import Func

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


def pack_service_lambda(
    service_file: str, attr: str, dest: str, include, include_service_file_dir
):
    """Pack a service for deployment to lambda"""
    # a service file must be part of a module
    m = _import_module(file_module(service_file))
    service = getattr(m, attr)

    if not isinstance(service, Service):
        raise PackerError(f"Not a Service: '{attr}' in {service_file}")

    # Create the lambda content
    with tempfile.TemporaryDirectory() as d_name:

        # --> /EXE_PATH/...
        os.makedirs(join(d_name, EXE_PATH))
        for name, handler in service.handlers:
            executable = compiler.link(compiler.compile_all(handler), name)
            exe_dest = join(d_name, EXE_PATH, name + "." + c9e.FILE_EXT)
            c9e.dump(executable, exe_dest)

        # --> /src/service_file.py
        if include_service_file_dir:
            copytree(dirname(service_file), join(d_name, SRC_PATH))
        else:
            os.makedirs(join(d_name, SRC_PATH))
            copy(service_file, join(d_name, SRC_PATH, basename(service_file)))

        # --> /src/...
        for i in include:
            if os.path.isfile(i):
                copy(i, join(d_name, SRC_PATH, basename(i)))
            else:
                copytree(i, join(d_name, SRC_PATH, basename(normpath(i))))

        # TODO include "libs" somehow... But probably duplicating lambda-packer.
        # --> /src/c9
        # if "c9" not in include:
        #     copytree(dirname(__file__), join(d_name, "src", "c9"))

        # zip_from_dir should probably be moved to a shared utils module:
        c9e.zip_from_dir(d_name, dest)
