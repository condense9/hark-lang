import c9
from c9.infrastructure import ObjectStore
from c9.lang import *

BUCKET = ObjectStore("uploads")


@BUCKET.on_upload
def on_upload(obj):
    return If(validate(obj), process(obj), None)


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


SERVICE = Service(
    "Data Processor", handlers=[on_upload], include=[__file__, "lib", ...]
)
