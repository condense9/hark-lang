import logging
import random
import sys
from pathlib import Path

import pytest
import teal_lang.controllers.ddb_model as db
import teal_lang.examples as teal_examples
from teal_lang.machine.types import TlType, to_py_type, to_teal_type
from teal_lang.run.dynamodb import run_ddb_local, run_ddb_processes
from teal_lang.run.local import run_local

LOG = logging.getLogger(__name__)

CALL_METHODS = [
    run_local,
    pytest.param(run_ddb_local, marks=[pytest.mark.slow]),
    pytest.param(run_ddb_processes, marks=[pytest.mark.slow]),
]

# Find all examples dir and test them
EXAMPLES_SUBDIR = Path(__file__).parent / "examples"
EXAMPLE_NAMES = [p.stem for p in Path(EXAMPLES_SUBDIR).glob("*.yaml")]

TESTS = teal_examples.load_examples(EXAMPLE_NAMES, EXAMPLES_SUBDIR)

IDS = [f"{filepath.stem}-{fn}[{i}]" for i, (filepath, fn, _, _) in enumerate(TESTS)]


def setup_module(module):
    # So that the examples can import their Python code
    sys.path.append(str(EXAMPLES_SUBDIR))


@pytest.fixture(autouse=True)
def session_db(pytestconfig):
    """Initialise the Teal sessions DynamoDB table"""
    if pytestconfig.getoption("--runslow"):
        if db.Session.exists():
            db.Session.delete_table()
        db.Session.create_table(
            read_capacity_units=1, write_capacity_units=1, wait=True
        )
        db.init_base_session()


@pytest.mark.parametrize("filename,function,args,expected", TESTS, ids=IDS)
@pytest.mark.parametrize("call_method", CALL_METHODS)
def test_example(filename, function, args, expected, call_method):
    seed = random.randint(0, 100000)
    random.seed(seed)
    LOG.info("Random seed: %d", seed)

    result = call_method(filename, function, list(map(to_teal_type, args)))

    # controllers should return normal python types
    assert not isinstance(result, TlType)

    assert result == expected
