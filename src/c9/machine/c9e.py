"""Define dumper/loader for the C9 executable file"""

import importlib
import logging
import os
import stat
import pickle
import shutil
import tempfile
from collections import namedtuple
from os.path import join
from zipfile import ZipFile

from . import instruction_from_repr
from .executable import Executable

logger = logging.getLogger()

# TODO validation of the code?? Versions..

# TODO security https://www.synopsys.com/blogs/software-security/python-pickling/

DEFAULT_MODE = stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH


def dump_c9e(
    executable: Executable, dest: str, main_file, includes=[], dest_mode=DEFAULT_MODE
):
    code = "\n".join(map(str, executable.code))

    with tempfile.TemporaryDirectory() as d_name:
        with open(join(d_name, "code.txt"), "w") as pf:
            pf.write(code)
        with open(join(d_name, "locations.pkl"), "wb") as pf:
            pickle.dump(executable.locations, pf, fix_imports=False)
        with open(join(d_name, "modules.txt"), "w") as pf:
            pf.write("\n".join(executable.modules.keys()))
        with open(join(d_name, "top_module_name.txt"), "w") as f:
            f.write(executable.name)

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
                        logger.info(f"Adding {name}")
            shutil.copy(zipf.name, dest)
            # https://stackoverflow.com/questions/10541760/can-i-set-the-umask-for-tempfile-namedtemporaryfile-in-python
            os.chmod(dest, dest_mode)
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

    return Executable(locations, code, modules, top_module_name)
