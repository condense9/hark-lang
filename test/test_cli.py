"""Test the Hark command line tool"""
from pathlib import Path
from subprocess import PIPE, Popen

EXAMPLES_SUBDIR = Path(__file__).parent / "examples"


def hark_cli(*args):
    """Run Hark cli command line and return (decoded) outputs"""
    p = Popen(
        ["python", "-m", "hark_lang.cli.main", *args],
        stdout=PIPE,
        stderr=PIPE,
        stdin=PIPE,
    )
    stdout, stderr = p.communicate()
    return stdout.decode(), stderr.decode(), p.returncode


def test_asm():
    """Test bytecode listing"""
    path = EXAMPLES_SUBDIR / "hello_world.hk"
    stdout, stderr, code = hark_cli("asm", path)
    assert not code
    assert ";; #0:main:" in stdout
    assert "BYTECODE" in stdout
    assert "BINDINGS" in stdout


def test_run():
    """Test just running a file"""
    path = EXAMPLES_SUBDIR / "hello_world.hk"
    stdout, stderr, code = hark_cli(path)
    assert not code
    assert stdout == "Hello World!\nHello World!\n"
