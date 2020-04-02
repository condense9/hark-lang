import logging
import os
import os.path
import tempfile
from os.path import dirname, join

import pytest

import c9.machine.c9e as c9e
from c9.compiler import compile_all, link
from c9.machine import Executable

from .handlers import conses, mapping

TESTS = [
    # --
    ("mapping", mapping.main),
    ("conses", conses.main),
]


@pytest.mark.parametrize("args", TESTS)
def test_dump_and_load(args):
    name = args[0]
    handler = args[1]
    moddir = join(dirname(__file__), "handlers")

    zipfile = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    logging.info(f"Created {zipfile} in test (will clean up afterwards)")

    original_exe = link(compile_all(handler), name)
    c9e.dump(original_exe, zipfile.name)
    loaded_exe = c9e.load(zipfile.name, [moddir])

    os.unlink(zipfile.name)

    assert isinstance(loaded_exe, Executable)
    assert loaded_exe.name == original_exe.name
    for a, b in zip(loaded_exe.code, original_exe.code):
        assert a == b
