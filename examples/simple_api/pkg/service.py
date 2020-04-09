import c9.service
from c9.lang import *
from c9.infrastructure import KVStore
from c9.stdlib.http import HttpHandler, OkJson, Error
from c9.stdlib import C9List
import os.path

from . import lib

DB = KVStore("todos", attrs=dict(todo_id="S"), keys=dict(todo_id="HASH"),)


@HttpHandler("POST", "/new-todo")
def add_todo(event, context):
    new_todo = lib.create_todo(DB, event, context)
    return If(new_todo, OkJson(new_todo), Error(500))


@HttpHandler("GET", "/")
def index(event, context):
    return OkJson(lib.list_todos(DB, event, context))


SERVICE = c9.service.Service(
    "Simple To-Do List", handlers=[add_todo, index], include=[os.path.dirname(__file__)]
)
