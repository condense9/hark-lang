from c9c.machine import Executable
from c9c.loader import load_executable
import os.path


def test_loader():
    exe = load_executable("mapping", "test/handlers")
    assert isinstance(exe, Executable)
