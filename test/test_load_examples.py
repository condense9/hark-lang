from pathlib import Path

import hark_lang.examples as hark_examples


def test_load_examples():
    examples = hark_examples.load_examples(
        ["kitchen_sink"], Path(__file__).parent / "examples"
    )
    assert len(examples) > 0
    assert isinstance(examples[0][0], Path)
    assert examples[0][0].name == "kitchen_sink.hk"
    assert examples[0][1:] == ("hello", [], "hello world")
