"""Define dumper/loader for the C9 executable file"""

import importlib
import logging
import os
import inspect
import stat
import json
import shutil
import tempfile
from collections import namedtuple
from os.path import join
import zipfile

from . import MFCall, Instruction
from .executable import Executable

logger = logging.getLogger()

# TODO validation of the code?? Versions..

# TODO security https://www.synopsys.com/blogs/software-security/python-pickling/

DEFAULT_MODE = stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH

FILE_EXT = "c9e"


# Instead of packing the python into the exe, make it the user's job to
# distribute the source alongside the exe. Of course I would just make a packer
# for that (Service packer).
#
# Inputs:
# - executables (handlers)
# - source code files []

# This module should just handle Executable to/from disk. Nothing more.


def zip_from_dir(path, zipf: str):
    """Zip all contents of PATH into ZIPF"""
    with zipfile.ZipFile(zipf, "w") as z:
        for root, dirs, files in os.walk(path):
            for f in files:
                name = join(root, f)
                arcname = name[len(path) :]
                z.write(name, arcname=arcname)
                logger.info(f"Zipped {name} -> {arcname}")


def dump(executable: Executable, dest: str, dest_mode=DEFAULT_MODE):
    """Save Executable to disk"""
    with tempfile.TemporaryDirectory() as d_name:
        with open(join(d_name, "code.json"), "w") as pf:
            data = [
                [i.name, i.operands]
                if not isinstance(i, MFCall)
                else ["MFCALL", translate_mfcall_operands(i)]
                for i in executable.code
            ]
            json.dump(data, pf)
        with open(join(d_name, "locations.json"), "w") as pf:
            json.dump(executable.locations, pf)
        with open(join(d_name, "top_module_name.txt"), "w") as f:
            f.write(executable.name)

        zip_from_dir(d_name, dest)


class LoadError(Exception):
    """Could not load a C9 executable file"""


def load(exe_file: str, searchpaths: list) -> Executable:
    """Load an executable from disk

    searchpath: where to search for python modules for foreign calls

    """
    with tempfile.TemporaryDirectory() as d:
        try:
            with zipfile.ZipFile(exe_file, "r") as f:
                f.extractall(d)
        except zipfile.BadZipFile:
            raise LoadError("Bad file format")

        with open(join(d, "top_module_name.txt"), "r") as f:
            top_module_name = f.read().strip()
        with open(join(d, "code.json"), "r") as cf:
            code = json.load(cf)
        with open(join(d, "locations.json"), "r") as pf:
            locations = json.load(pf)

    instructions = []

    for item in code:
        name, ops = tuple(item)

        if name == "MFCALL":
            instr = retrieve_mfcall(ops, searchpaths)
        else:
            instr = Instruction.from_name(name, *ops)

        instructions.append(instr)

    return Executable(locations, instructions, top_module_name)


def translate_mfcall_operands(instruction) -> tuple:
    fn = instruction.operands[0]
    num_args = instruction.operands[1]
    return (inspect.getmodule(fn).__name__, fn.__name__, num_args)


def retrieve_mfcall(ops, searchpaths):
    # paired with translate_mfcall_operands
    fn = find_function(ops[0], ops[1], searchpaths)
    return MFCall(fn, ops[2])


def find_function(modname, fnname, searchpaths: list):
    """Find the specified python function """
    # print(f"Loading {modname}.{fnname} from {searchpaths}")
    spec = importlib.machinery.PathFinder.find_spec(modname, path=searchpaths)
    if not spec:
        raise Exception(f"Can't find {modname}.{fnname} in {searchpaths}")
    m = spec.loader.load_module()
    fn = getattr(m, fnname)
    # Hackyyyy - Foreign
    if hasattr(fn, "original_function"):
        fn = fn.original_function
    return fn
