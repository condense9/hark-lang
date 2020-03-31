"""Loading / importing"""

from .compiler import link, compile_all
from .machine import Executable
import importlib.util
import importlib.machinery
import warnings


# https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
# https://docs.python.org/3/library/importlib.html#importlib.util.spec_from_loader
def load_executable(module: str, searchpath) -> Executable:
    spec = importlib.machinery.PathFinder.find_spec(module, path=[searchpath])
    if not spec:
        raise Exception(f"Could not import {module} from {searchpath}")
    m = spec.loader.load_module()
    executable = link(compile_all(m.main), exe_name=module)
    return executable
