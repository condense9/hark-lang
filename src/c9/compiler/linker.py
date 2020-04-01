"""Link a bunch of functions together into an executable"""

from .. import machine as m
import importlib
from ..machine.executable import Executable


class LinkError(Exception):
    """Something went wrong while linking"""


def link(
    defs, searchpath, entrypoint_fn="F_main", num_args=1, exe_name=None
) -> Executable:
    """Link a bunch of definitions into a single executable"""
    preamble_length = 1
    defs_code = []
    locations = {}

    for name, instructions in defs.items():
        locations[name] = len(defs_code) + preamble_length
        defs_code += instructions

    entrypoint = len(defs_code)  # *relative* jump to after defs_code
    preamble = [m.Jump(entrypoint)]

    if len(preamble) != preamble_length:
        # Defensive coding
        raise LinkError(f"Preamble length {len(preamble)} != {preamble_length}")

    if entrypoint_fn not in defs:
        raise LinkError(f"{entrypoint_fn} not found in defitions")

    code = [
        *preamble,
        *defs_code,
        # actual entrypoint:
        m.PushV(entrypoint_fn),
        m.Call(num_args),
        m.Wait(0),  # Always wait for the last value to resolve
        m.Return(),
        # NOTE -- no Return at the end. Nothing to return to!
    ]

    modules = {
        i.operands[0]: load_module(i.operands[0], searchpath)
        for i in code
        if isinstance(i, m.MFCall)
    }

    return Executable(locations, code, modules, name=exe_name)


def load_module(name, searchpath):
    if name == "__main__":
        raise Exception("ugh")
    else:
        spec = importlib.machinery.PathFinder.find_spec(name, path=[searchpath])
        return spec.loader.load_module()
