# Example :: Super Simple API

This is a very simple web application with a Database backend.

Infrastructure:
- Lambda to handle the requests
- Key-Value store database


### Preface: Imports

```python tangle:service.py
import c9.service
from c9.lang import *
from c9.infrastructure import KVStore
from c9.stdlib.http import HttpHandler, OkJson, ErrorJson
from c9.stdlib import Eq

from . import lib
```

## Let's do it!

First, the database (currently implemented on DynamoDB).

```python tangle:service.py
DB = KVStore(
    "todos",
    attrs=dict(todo_id="S"),
    keys=dict(todo_id="HASH"),
)
```

Next, what events have we got?
- GET /
- POST /new-todo

Easy.

```python tangle:service.py
@HttpHandler("POST", "todos")
def add_todo(event, context):
    new_todo = lib.create_todo(DB, event, context)
    return If(Eq(new_todo, False),
              ErrorJson(500, "Failed inserting into DB"),
              OkJson(new_todo))

@HttpHandler("GET", "todos")
def index(event, context):
    return OkJson(lib.list_todos(DB, event, context))
    
@HttpHandler("POST", "echo")
@Foreign
def echo_it(event, context):
    return dict(statusCode=200, body=event)
```

This will create an API with two resources:
- *todos*
- *echo*

And the *todos* resource has two methods (GET and POST).

And create the service:

```python tangle:service.py
SERVICE = c9.service.Service(
    "Simple To-Do List",
    handlers=[add_todo, index, echo_it],
)
```

### Compile the service

```shell
make deps build
```

The result is a folder (`build`) with
- the lambda source code to implement the service
- Terraform infrastructure as code
- a `deploy.sh` script to deploy it

