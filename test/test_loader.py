import os.path

import pytest

import c9.machine.c9e as c9e
from c9.machine import Executable


def test_load():
    exe = c9e.load("handlers/mapping.zip")
    assert isinstance(exe, Executable)
