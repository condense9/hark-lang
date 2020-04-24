"""Link a bunch of functions together into an executable"""

from .. import machine as m
from ..machine.executable import Executable
from ..machine import types as mt


class LinkError(Exception):
    """Something went wrong while linking"""


def link(defs, foreigns, exe_name, *, entrypoint_fn="F_main", num_args=1) -> Executable:
    """Link a bunch of definitions into a single executable"""
    if not isinstance(entrypoint_fn, str):
        raise ValueError(entrypoint_fn)

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
        raise LinkError(f"{entrypoint_fn} not found in definitions: {defs.keys()}")

    code = [
        *preamble,
        *defs_code,
        # actual entrypoint:
        m.PushV(mt.C9Function(entrypoint_fn)),
        m.Call(num_args),
        m.Wait(0),  # Always wait for the last value to resolve
        m.Return(),
        # NOTE -- no Return at the end. Nothing to return to!
    ]

    return Executable(locations, foreigns, code)
