# Example :: Super Simple API

This is a very simple web application with a Database backend.

Infrastructure:
- Lambda to handle the requests
- Key-Value store database


### Preface: Imports

```python tangle:service.py
import c9.service
from c9.lang import *
from c9.infrastructure import make_kvstore, db_insert, db_scan
from c9.stdlib.http import HttpHandler, OkJson, Error
from c9.stdlib import C9List
import os.path
```

## Let's do it!

First, the database (currently implemented on DynamoDB).

```python tangle:service.py
DB = make_kvstore(
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
def add_todo(request):
    new_todo = db_insert(DB, C9List("complete", False,
        "description", get_description(request)))
    return If(new_todo, OkJson(new_todo), Error(500))

@HttpHandler("GET", "/")
def index(request):
    return OkJson(db_scan(DB, "ALL_ATTRIBUTES", 20))
```

C9 doesn't have many native types, so some Python is necessary to deconstruct
dictionaries.

```python tangle:service.py
@Foreign
def get_description(request):
    return request["body"]["description"]
```

Finally, create the service:

```python tangle:service.py
SERVICE = c9.service.Service(
    "Simple To-Do List",
    handlers=[add_todo, index],
    pipeline=c9.service.TF_PIPELINE,
    include=[os.path.dirname(__file__)]
)
```

### Compile the service

```shell
c9c service service.py SERVICE -o build
```

The result is a folder (`build`) with
- the source code to implement the service (ie this file)
- a `deploy.sh` script to deploy it

