import logging
import sys
import random
from pathlib import Path

import pytest
import teal_examples
from teal.machine.types import TlType, to_py_type, to_teal_type
from teal.run.dynamodb import run_ddb_local, run_ddb_processes
import teal.controllers.ddb_model as db
from teal.run.local import run_local

LOG = logging.getLogger(__name__)

CALL_METHODS = [
    run_local,
    run_ddb_local,
    pytest.param(run_ddb_processes, marks=[pytest.mark.slow]),
]

# Find all examples dir and test them
EXAMPLES_SUBDIR = Path(__file__).parent / "examples"
EXAMPLE_NAMES = [p.stem for p in Path(EXAMPLES_SUBDIR).glob("*.yaml")]

TESTS = teal_examples.load_examples(EXAMPLE_NAMES, EXAMPLES_SUBDIR)

IDS = [f"{filepath.stem}-{fn}[{i}]" for i, (filepath, fn, _, _) in enumerate(TESTS)]


def setup_module():
    # So that the examples can import their Python code
    sys.path.append(str(EXAMPLES_SUBDIR))

    # And ensure the database table exists
    if db.Session.exists():
        db.Session.delete_table()
    db.Session.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
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
