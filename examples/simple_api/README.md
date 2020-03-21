# Example :: Super Simple API

This is the simplest possible API endpoint.

Infrastructure:
- Lambda to handle the request

Dpeloyment outputs:
- The endpoint URL

Note: no API gateway; this is just one function.


### Preface: Imports

Very little is needed.

```python tangle:service.py
import c9c
from c9c.http import http_get, Response
```


## Let's do it!

ok, what events have we got?
- GET /

Easy.

```python tangle:service.py
@http_get("/")
def handler(request):
    return Response(200, "Hello world!")
```


### Compile the service

```python tangle:service.py
if __name__ == '__main__':
    import c9c
    import typing as t

    simple = c9c.Service(
        handlers = [handler]
        export_methods = []
        outputs = [handler.endpoint_url]
    )

    c9c.compiler_cli(simple)
```

The result is a folder with
- the source code to implement the service (ie this file)
- 
