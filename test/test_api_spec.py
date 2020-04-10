import c9.infrastructure as inf
from c9.synthesiser.api_spec import get_api_spec
from openapi_spec_validator import validate_spec

from pprint import pprint


def test_get_api_spec():
    endpoints = [
        inf.HttpEndpoint(
            "new_todo", "POST", "/todo", "new_todo_fn", {}, dict(description="string")
        ),
        inf.HttpEndpoint(
            "get_todo",
            "GET",
            "/todo/{todo_id}",
            "get_todo_fn",
            dict(todo_id="string"),
            None,
        ),
        inf.HttpEndpoint("get_index", "GET", "/", "get_index_fn", None, None),
    ]
    spec = get_api_spec("Test API", "0.1.0", endpoints)
    assert isinstance(spec, dict)
    pprint(spec)

    # https://github.com/p1c2u/openapi-spec-validator
    validate_spec(spec)
