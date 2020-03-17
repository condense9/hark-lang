# Example :: Data Processing Pipeline

Let's build a simple data processing pipeline. This might have some custom
infrastructure, and no HTTP events.

App requirements
- monitor several buckets for uploads
- check the file format
- write metadata about the file to two locations

### Preface: Imports

A few things are needed.

```python tangle:service.py
"""A very simple imageboard"""

import c9c.events as e
import c9c.services as s
from c9c.lang import Func, If
```


## Let's do it!

Ok, what events have we got?
- A file is uploaded to one of several S3 buckets

Easy.


### Handle the bucket event

```python
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

```

### Compile the service

```python tangle:service.py
if __name__ == '__main__':
    import c9c
    import typing as t

    class DPP(c9c.Service):
        options = {"buckets": t.List[str]}
        export_methods = []
        outputs = []

    c9c.compiler_cli(DPP)
```
