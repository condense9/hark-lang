from c9c.machine import Executable
from c9c.loader import load_executable
import os.path


def test_loader():
    exe = load_executable(
        "mapping", os.path.join(os.path.dirname(__file__), f"handlers/mapping.py")
    )
    assert isinstance(exe, Executable)
