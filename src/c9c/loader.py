"""Loading / importing"""

from .compiler import link, compile_all
from .machine import Executable
import importlib.util


def load_executable(module: str, path) -> Executable:
    spec = importlib.util.spec_from_file_location(module, path)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    executable = link(compile_all(foo.main), exe_name=module)
    return executable
