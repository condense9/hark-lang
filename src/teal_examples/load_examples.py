import yaml
from typing import List, Tuple
from pathlib import Path

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
    examples = []
    for name in names:
        filename = exdir / (name + ".tl")
        with open(exdir / (name + ".yaml"), "r") as cf:
            # use FullLoader to load types correctly. Looks like BaseLoader
            # loads everything as string
            config = yaml.load(cf, Loader=yaml.FullLoader)

        for function, vectors in config.items():
            for args, ret in vectors:
                examples.append((filename, function, args, ret))

    return examples
