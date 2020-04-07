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
import c9
from c9.infrastructure import ObjectStore
from c9.lang import *
```


## Let's do it!

Ok, what events have we got?
- A file is uploaded to one of several S3 buckets

Easy.


### Handle the bucket event

Create the bucket and the event handler.

```python tangle:service.py
BUCKET = ObjectStore("uploads")

@BUCKET.on_upload
def on_upload(obj):
    return If(validate(obj), process(obj), None)    
```

Process the object:

```python tangle:service.py
@Function
def process(obj):
    chunks = Async(get_chunks(obj))
    metadata = Async(get_metadata(obj))
    results = Map(process_chunk, chunks)
    return save_to_db(metadata, results)

@Foreign
def process_chunk(chunk):
    # long running function
    pass

@Foreign
def save_to_db(metadata, results):
    # ...
    pass
```

And the other methods:

```python tangle:service.py
@Async
@Native
def get_chunks(obj):
    # ...
    pass
    
@Async
@Native
def get_metadata(obj):
    # ...
    pass

```

### Create the service

```python tangle:service.py
SERVICE = Service(
    "Data Processor",
    handlers=[on_upload],
    include=[__file__, "lib", ...]
)
```
