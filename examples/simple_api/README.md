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
from c9c.handlers import HttpHandler, Response
```


## Let's do it!

ok, what events have we got?
- GET /

Easy.

```python tangle:service.py
@HttpHandler("GET", "/")
def index_foo(event, context):
    return Response(200, "Hello world!")
```

### Create the service

```python tangle:service.py
SERVICE = c9c.Service(
    name="foo",
    entrypoint=__file__,
    # extra_source =
    handlers=[index_foo],
    export_methods=[],
    # outputs=[handler.endpoint_url],
)

```

### Compile the service

```python tangle:service.py

def main():
    # c9c.cli.generate(SERVICE)
    c9c.synthesiser.generate(SERVICE, "./build")
    
if __name__ == '__main__':
    main()
```

The result is a folder with
- the source code to implement the service (ie this file)
- 


For testing:

```
if __name__ == "__main__":
    import c9c.compiler
    import c9c.synthesiser

    print(c9c.synthesiser.generate(SERVICE, "./build"))
```
