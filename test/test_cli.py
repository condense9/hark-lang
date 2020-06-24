"""Test the Teal command line tool"""
from pathlib import Path
from subprocess import PIPE, Popen

EXAMPLES_SUBDIR = Path(__file__).parent / "examples"


def teal_cli(*args):
    """Run Teal cli command line and return (decoded) outputs"""
    p = Popen(
        ["python", "-m", "teal_lang.cli.main", *args],
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
    )
    stdout, stderr = p.communicate()
    return stdout.decode(), stderr.decode(), p.returncode


def test_asm():
    """Test bytecode listing"""
    path = EXAMPLES_SUBDIR / "hello_world.tl"
    stdout, stderr, code = teal_cli("asm", path)
    assert not code
    assert ";; #0:main:" in stdout
    assert "BYTECODE" in stdout
    assert "BINDINGS" in stdout


def test_run():
    """Test just running a file"""
    path = EXAMPLES_SUBDIR / "hello_world.tl"
    stdout, stderr, code = teal_cli(path)
    assert not code
    assert stdout == "\nHello World!\nHello World!\n"
