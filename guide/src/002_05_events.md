# Events

Events supported:
- REST API calls
- Object store events

Handlers are created with decorators.


## `@HttpHandler`

Define a C9 Func that is called when a particular HTTP/REST endpoint is called.

```python
from c9.http import HttpHandler, OkJson

@HttpHandler(<method>, <resource>)
def the_handler(event, context):
    # ... this is a C9 Func
    return OkJson({"message": "success!"})
```

| Parameter | Type                             | Example         |
|-----------|----------------------------------|-----------------|
| method    | HTTP verb                        | GET, POST, ...  |
| resource  | REST resource (no leading slash) | "pets", "books" |

The handler will be called with the raw AWS Lambda (event, context) tuple, and
must return a JSON response in the correct format. There are some helpers for
this:

- `OkJson(body)` returns HTTP 200 with the given body as JSON
- `ErrorJson(message)` returns HTTP 500 with the given message

This may be abstracted in future to support other clouds...


## `@ObjectUpload`

TODO!
