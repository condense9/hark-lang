import logging
import random
import sys
from pathlib import Path

import pytest
import hark_lang.controllers.ddb_model as db
import hark_lang.examples as hark_examples
from hark_lang.machine.types import TlType, to_py_type, to_hark_type
from hark_lang.run.dynamodb import run_ddb_local, run_ddb_processes
from hark_lang.run.local import run_local

LOG = logging.getLogger(__name__)

CALL_METHODS = [
    run_local,
    pytest.param(run_ddb_local, marks=[pytest.mark.slow, pytest.mark.ddblocal]),
    pytest.param(run_ddb_processes, marks=[pytest.mark.slow, pytest.mark.ddblocal]),
]

# Find all examples dir and test them
EXAMPLES_SUBDIR = Path(__file__).parent / "examples"
EXAMPLE_NAMES = [p.stem for p in Path(EXAMPLES_SUBDIR).glob("*.hk")]

TESTS = hark_examples.load_examples(EXAMPLE_NAMES, EXAMPLES_SUBDIR)

IDS = [f"{filepath.stem}-{fn}[{i}]" for i, (filepath, fn, _, _) in enumerate(TESTS)]


def setup_module(module):
    # So that the examples can import their Python code
    sys.path.append(str(EXAMPLES_SUBDIR))


@pytest.fixture(autouse=True)
def session_db(pytestconfig):
    """Initialise the Hark sessions DynamoDB table"""
    if not pytestconfig.getoption("testddb"):
        return

    from . import test_controllers

    test_controllers.setup_module(None)


@pytest.mark.parametrize("filename,function,args,expected", TESTS, ids=IDS)
@pytest.mark.parametrize("call_method", CALL_METHODS)
def test_example(filename, function, args, expected, call_method):
    seed = random.randint(0, 100000)
    random.seed(seed)
    LOG.info("Random seed: %d", seed)

    # args will all be strings
    result = call_method(filename, function, args)

    # controllers should return normal python types
    assert not isinstance(result, TlType)

    assert result == expected
