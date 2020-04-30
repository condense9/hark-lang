import logging
import random
from pathlib import Path

import pytest
import teal_examples
from teal.machine.types import TlType, to_py_type, to_teal_type
from teal.run.dynamodb import run_ddb_local, run_ddb_processes
from teal.run.local import run_local

LOG = logging.getLogger(__name__)

SEED = random.randint(0, 100000)
random.seed(SEED)
LOG.info("Random seed", SEED)


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


@pytest.mark.parametrize("filename,function,args,expected", TESTS, ids=IDS)
@pytest.mark.parametrize("call_method", CALL_METHODS)
def test_example(filename, function, args, expected, call_method):
    result = call_method(filename, function, list(map(to_teal_type, args)))

    # controllers should return normal python types
    assert not isinstance(result, TlType)

    assert result == expected
