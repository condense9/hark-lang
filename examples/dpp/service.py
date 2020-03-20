"""A very simple imageboard"""

import c9c.events as e
import c9c.services as s
from c9c.lang import Func, If
@e.object.uploaded(buckets=DPP.options.buckets)
def handle_upload(obj):
    return If(validate(obj), process(obj), None)

@Func
def process(obj):
    """The data processing workflow"""
    meta1 = get_metadata1(obj)
    meta2 = get_metadata2(obj)
    Return Do(write_db1(meta1), write_db2(meta2))

@Foreign
def write_to_db1(meta):
    pass

@Foreign
def write_to_db2(meta):
    pass

if __name__ == '__main__':
    import c9c
    import typing as t

    class DPP(c9c.Service):
        options = {"buckets": t.List[str]}
        export_methods = []
        outputs = []

    c9c.compiler_cli(DPP)
