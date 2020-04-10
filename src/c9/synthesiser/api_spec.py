"""Convert HttpEndpoint to OpenAPI spec"""

from typing import List, Dict

from ..infrastructure import HttpEndpoint


def _get_paths(endpoints) -> List[str]:
    """Get the unique API paths in endpoints"""
    return list(set(e.infra_spec.path for e in endpoints))


def _get_responses(e: HttpEndpoint) -> Dict:
    # Return http://spec.openapis.org/oas/v3.0.3#responses-object
    # NOTE - not implemented in HttpEndpoint
    # Actually, this could be inferred from the Func at compile-time...
    # Map of name -> http://spec.openapis.org/oas/v3.0.3#response-object
    return {"200": dict(description="Ok")}


def _get_apigateway_integration(e: HttpEndpoint) -> Dict:
    # We can't get access to the lambda ARN - the HttpEndpoint only knows about
    # the function name. We could drop in a template variable if we really
    # wanted to...
    # https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions-integration.html
    raise NotImplementedError
    region = e.region
    lambda_arn = TODO  # Unknown!
    return dict(
        uri=f"arn:aws:apigateway:{e.region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
        httpMethod=e.method,
        type="aws_proxy",
    )


def _get_operation_object(e: HttpEndpoint) -> List[Dict]:
    """Get the parameters for a given endpoint"""
    # Return http://spec.openapis.org/oas/v3.0.3#operation-object
    return {
        "responses": _get_responses(e),
        # "x-amazon-apigateway-integration": _get_apigateway_integration(e),
    }


def _get_parameters(e: HttpEndpoint) -> List:
    param = lambda name, vtype, kind: {
        "name": name,
        "in": kind,
        "required": True,
        "schema": {"type": vtype},
    }
    body_params = [
        param(name, vtype, "body") for name, vtype in e.infra_spec.body_params.items()
    ]
    path_params = [
        param(name, vtype, "path") for name, vtype in e.infra_spec.path_params.items()
    ]
    query_params = [
        param(name, vtype, "query") for name, vtype in e.infra_spec.query_params.items()
    ]
    return body_params + query_params + path_params


def _get_path_items(endpoints, path) -> Dict[str, Dict]:
    """Get the HTTP methods and parameters for a given path"""
    # Returns http://spec.openapis.org/oas/v3.0.3#path-item-object
    operations = {
        e.infra_spec.method.lower(): _get_operation_object(e)
        for e in endpoints
        if e.infra_spec.path == path
    }
    # All endpoints at this point have the same path. Icky
    parameters = _get_parameters(
        next(e for e in endpoints if e.infra_spec.path == path)
    )
    return {**operations, "parameters": parameters}


def get_api_spec(
    title, version, endpoints: List[HttpEndpoint], extra_info=None, **kwargs
) -> dict:
    # Spec spec: http://spec.openapis.org/oas/v3.0.3#fixed-fields
    if not extra_info:
        extra_info = {}
    info = dict(title=title, version=version, **extra_info)
    paths = {path: _get_path_items(endpoints, path) for path in _get_paths(endpoints)}
    return dict(openapi="3.0.3", info=info, paths=paths, **kwargs)
