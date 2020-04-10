import c9.service
from c9.lang import *
from c9.infrastructure import KVStore
from c9.stdlib.http import HttpHandler, OkJson, ErrorJson
from c9.stdlib import Eq

from . import lib

DB = KVStore("todos", attrs=dict(todo_id="S"), keys=dict(todo_id="HASH"),)


@HttpHandler("POST", "todos")
def add_todo(event, context):
    new_todo = lib.create_todo(DB, event, context)
    return If(
        Eq(new_todo, False),
        ErrorJson(500, "Failed inserting into DB"),
        OkJson(new_todo),
    )


@HttpHandler("GET", "todos")
def index(event, context):
    return OkJson(lib.list_todos(DB, event, context))


@HttpHandler("POST", "echo")
@Foreign
def echo_it(event, context):
    return dict(statusCode=200, body=event)


SERVICE = c9.service.Service("Simple To-Do List", handlers=[add_todo, index, echo_it],)
