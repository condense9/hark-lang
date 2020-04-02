"""Python File -> C9 Executable File"""

import importlib
from os.path import basename, dirname, splitext

from . import compiler
from .machine import c9e


# OLD
def dump(main_file: str, dest: str, includes: list = []):
    """Compile and dump"""
    module_name = splitext(basename(main_file))[0]
    module_path = dirname(main_file)
    spec = importlib.util.spec_from_file_location(module_name, main_file)
    m = spec.loader.load_module()
    executable = compiler.link(compiler.compile_all(m.main), module_name)
    c9e.dump(executable, dest)
