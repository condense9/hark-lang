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
from c9.stdlib.http import HttpHandler, OkJson, Error
from c9.stdlib import C9List
import os.path

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
@HttpHandler("POST", "/new-todo")
def add_todo(event, context):
    new_todo = lib.create_todo(DB, event, context)
    return If(new_todo, OkJson(new_todo), Error(500))

@HttpHandler("GET", "/")
def index(event, context):
    return OkJson(lib.list_todos(DB, event, context))
```

And create the service:

```python tangle:service.py
SERVICE = c9.service.Service(
    "Simple To-Do List",
    handlers=[add_todo, index],
)
```

### Compile the service

```shell
c9c service service.py SERVICE -o build
```

The result is a folder (`build`) with
- the source code to implement the service (ie this file)
- a `deploy.sh` script to deploy it

