"""Manage importing python (foreign) functions"""

import builtins
import importlib
import logging
import os
import sys
import traceback
from functools import lru_cache

from ..exceptions import UserResolvableError

LOG = logging.getLogger(__name__)


class ImportPyError(UserResolvableError):
    """Error importing some code from Python"""


@lru_cache
def _load_module(modname):
    if modname == "__builtins__":
        if not os.getenv("ENABLE_IMPORT_BUILTIN", False):
            raise ImportPyError(
                "Cannot import from builtins.",
                "ENABLE_IMPORT_BUILTIN must be set to enable this.",
            )
        return builtins
    else:
        spec = importlib.util.find_spec(modname)
        if not spec:
            raise ImportPyError(f"Cannot find Python module `{modname}'", "")
        try:
            return spec.loader.load_module()
        except Exception as exc:
            tb = "".join(traceback.format_exception(*sys.exc_info()))
            raise ImportPyError(
                f"Could not load Python module `{modname}'.", tb
            ) from exc


def import_python_function(fnname, modname):
    """Load function

    If modname is None, fnname is taken from __builtins__ (e.g. 'print')

    PYTHONPATH must be set up already.
    """
    LOG.info(f"Starting import {modname}.{fnname}")
    m = _load_module(modname)
    try:
        fn = getattr(m, fnname)
    except AttributeError as exc:
        raise ImportPyError(
            f"Could not find {fnname} in {modname}.",
            f"({modname}.{fnname} -> AttributeError)",
        ) from exc

    LOG.info(f"Imported {modname}.{fnname}")
    return fn
