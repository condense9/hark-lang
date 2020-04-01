"""Executable <--> FILE"""

import os
import importlib
import pickle
import shutil
import tempfile
from collections import namedtuple
from os.path import basename, dirname, join, splitext
from zipfile import ZipFile

from . import compiler
from .machine.executable import Executable
from .machine import instruction_from_repr

# TODO security https://www.synopsys.com/blogs/software-security/python-pickling/


# Executable Archive:
# - executable.pkl
# - src/


# Source dir:
# - something.py   :: def main(), import lib.foo, import other.bar
# - other.py
# - lib/foo.py


def dump(main_file, dest: str, includes=[]):
    module_name = splitext(basename(main_file))[0]
    module_path = dirname(main_file)
    spec = importlib.util.spec_from_file_location(module_name, main_file)
    m = spec.loader.load_module()
    executable = compiler.link(
        compiler.compile_all(m.main), module_path, exe_name=module_name
    )
    code = "\n".join(map(str, executable.code))

    with tempfile.TemporaryDirectory() as d_name:
        with open(join(d_name, "code.txt"), "w") as pf:
            pf.write(code)
        with open(join(d_name, "locations.pkl"), "wb") as pf:
            pickle.dump(executable.locations, pf, fix_imports=False)
        with open(join(d_name, "modules.txt"), "w") as pf:
            pf.write("\n".join(executable.modules.keys()))
        with open(join(d_name, "top_module_name.txt"), "w") as f:
            f.write(module_name)

        shutil.copy(main_file, d_name)

        for i in includes:
            if os.path.isdir(i):
                shutil.copytree(i, d_name, follow_symlinks=False)
            else:
                shutil.copy(i, d_name)

            shutil.copy(i, d_name)

        zipf = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        try:
            with ZipFile(zipf, "w") as z:
                for root, dirs, files in os.walk(d_name):
                    for f in files:
                        name = join(root, f)
                        arcname = name[len(d_name) :]
                        z.write(name, arcname=arcname)
                        # print(name)
            shutil.copy(zipf.name, dest)
        finally:
            os.unlink(zipf.name)


def load(exe_file: str) -> Executable:
    with tempfile.TemporaryDirectory() as d:
        with ZipFile(exe_file, "r") as f:
            f.extractall(d)

        with open(join(d, "top_module_name.txt"), "r") as f:
            top_module_name = f.read().strip()

        spec = importlib.util.spec_from_file_location(
            top_module_name, join(d, f"{top_module_name}.py")
        )
        top_module = spec.loader.load_module()

        with open(join(d, "code.txt"), "r") as cf:
            code = [instruction_from_repr(line) for line in cf.read().split("\n")]

        with open(join(d, "modules.txt"), "r") as mf:
            module_names = mf.read().split("\n")

        with open(join(d, "locations.pkl"), "rb") as pf:
            locations = pickle.load(pf)

    modules = {}
    for modname in module_names:
        if modname == top_module_name:
            modules[modname] = top_module
        else:
            modules[modname] = getattr(top_module, modname)

    name = basename(exe_file)
    return Executable(locations, code, modules, name)
