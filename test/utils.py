"""Shared test utilities"""

import warnings
from typing import Dict, List

import c9c.compiler as compiler
import c9c.lang as l
import c9c.machine as m
from c9c.runtime.local import LocalRuntime, LocalState


def listing(code):
    print("\n".join(f"{i} | {a}" for i, a in enumerate(code)))


def list_defs(defs):
    for n, c in defs.items():
        print(f"{n}:")
        listing(c)


def run_dbg_local(executable, data, *, trace=True):
    """Run the machine locally and print lots of state"""
    probe = m.DebugProbe(trace=trace)
    machine = m.C9Machine(executable, data, LocalRuntime(), probe=probe)
    if trace:
        m.print_instructions(executable)
    machine.run()
    if trace:
        print("*** FINISHED")
        machine.state.show()


def check_data(data: LocalState, expected: LocalState):
    """Check that machine state matches expectation"""
    assert len(expected._ds) == len(data._ds)
    for i, (a, b) in enumerate(zip(expected._ds, data._ds)):
        assert i >= 0 and a == b


def check_exec(executable, data: LocalState, expected: LocalState, *, trace=False):
    """Run a program to termination, and check that the data stack is as expected"""
    run_dbg_local(executable, data, trace=trace)
    check_data(data, expected)


def check_compile_node(node, expected):
    """Check that the evaluation output is as expected"""
    result = [str(a) for a in compiler.compile_node(node).code]
    expected = [a.strip() for a in expected.split("\n")]
    expected = list(filter(lambda x: len(x), expected))  # Remove empty lines
    assert len(expected) == len(result)
    for i, (a, b) in enumerate(zip(result, expected)):
        assert i >= 0 and a.strip() == b.strip()


def check_compile_all(fn: l.Func, expected: Dict, allow_custom_validation=False):
    """Check that some function definitions are correct"""
    defs = compiler.compile_all(fn)
    for k in defs.keys():
        if k not in expected:
            warnings.warn(f"Skipping {k} - Expected output not given")
    for k in expected.keys():
        assert k in defs
        assert len(defs[k]) == len(expected[k])
        for i, (a, b) in enumerate(zip(defs[k], expected[k])):
            if isinstance(a, l.Builtin):
                # Awkward. Builtins take arguments in the source, but not in the
                # assembly. So this is to avoid having to instantiate real
                # builtins in EXPECTED
                assert k and i >= 0 and type(a) == b
            elif not isinstance(b, l.Node) and callable(b):
                if allow_custom_validation:
                    assert b(a)
                else:
                    raise Exception("Custom validation disabled")
            else:
                assert k and i >= 0 and a == b
