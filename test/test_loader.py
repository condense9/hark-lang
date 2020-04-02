import os.path

import pytest
from os.path import join, dirname

import c9.machine.c9e as c9e
from c9.machine import Executable


@pytest.mark.parametrize("name", ["mapping", "conses"])
def test_load(name):
    filename = join(dirname(__file__), "handlers", f"{name}.zip")
    exe = c9e.load(filename)
    assert isinstance(exe, Executable)
    assert exe.name == name
