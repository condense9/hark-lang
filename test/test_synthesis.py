"""Test the synthesiser!"""
import pytest

from c9.lang import infrastructure as inf
from c9.synthesiser import slcomponents as slc
from c9.synthesiser.exceptions import SynthesisException
from c9.synthesiser.synthstate import SynthState


def test_basic_pipeline():
    res = [
        inf.Function("foo"),
        inf.Function("bar"),
        inf.HttpEndpoint("get_foo", "/foo", "GET", "foo"),
        inf.ObjectStore("buc"),
    ]
    s1 = SynthState(res, [], [], "./code")
    s2 = slc.functions(s1)
    assert len(s2.iac) == 2

    with pytest.raises(SynthesisException):
        slc.api(s1)
    s3 = slc.api(s2)
    assert len(s3.iac) == 3

    s4 = slc.buckets(s3)
    assert len(s4.iac) == 4

    # TODO - more tests!

    bucket_iac = s4.iac[-1]()
    assert len(bucket_iac) > 0
    assert isinstance(bucket_iac, str)
    assert bucket_iac.startswith("buc:")
