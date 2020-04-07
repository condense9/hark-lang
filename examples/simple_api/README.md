# Example :: Super Simple API

This is a very simple web application with a Database backend.

Infrastructure:
- Lambda to handle the requests
- Key-Value store database


### Preface: Imports

```python tangle:service.py
import c9
from c9.lang import *
from c9.stdlib.http import Response
```

## Let's do it!

First, the database (currently implemented on DynamoDB).

```python tangle:service.py
DB = c9.infrastructure.KVStore(
    "todos",
    attrs=dict(todo_id="S", complete="B", description="S"),
    keys=dict(todo_id="HASH"),
)
```

Next, what events have we got?
- GET /
- POST /new-todo

Easy.

```python tangle:service.py
@c9.handlers.Http("POST", "/new-todo")
def add_todo(request):
    success, new_todo = DB.insert(
        complete=False, description=request.body["description"],
    )
    return If(success, Response(200, new_todo), Response(500))

@c9.handlers.Http("GET", "/")
def index(request):
    return Response(
        200, build_homepage_html(DB.scan(Select="ALL_ATTRIBUTES", Limit=20))
    )
```

Now we also need to implement the native function `build_homepage_html` to
actually render the HTML. This is evaluated at runtime, so use your favourite
template engine!

```python tangle:service.py
@Native
def build_homepage_html(todos):
    return "<html>... {{ todos }} ...</html>"
```

Finally, create the service:

```python tangle:service.py
SERVICE = Service(
    "Simple To-Do List",
    handlers=[add_todo, index],
    include=[__file__]
)
```

### Compile the service

```shell
c9c service service.py SERVICE -o build
```

The result is a folder (`build`) with
- the source code to implement the service (ie this file)
- a `deploy.sh` script to deploy it

