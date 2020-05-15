import yaml
import logging
from typing import List, Tuple
from pathlib import Path

LOG = logging.getLogger(__name__)

Filename = str
Function = str
Arguments = List
ExpectedResult = str
ExampleSpec = Tuple[Filename, Function, Arguments, ExpectedResult]


def load_examples(names: List[str], exdir: Path) -> List[ExampleSpec]:
    """Load Teal examples and their test vectors

    Parameters:
        names: List of names of examples to load
        exdir: Directory containing the examples and vectors
    """
    with open(exdir / "test_vecs.yaml", "r") as cf:
        # use FullLoader to load types correctly. Looks like BaseLoader
        # loads everything as string
        vectors = yaml.load(cf, Loader=yaml.FullLoader)

    examples = []
    for name in names:
        filename = exdir / (name + ".tl")
        try:
            for function, (args, ret) in vectors[name].items():
                examples.append((filename, function, args, ret))
        except KeyError:
            LOG.warning(f"No test vectors for {name}")

    return examples
