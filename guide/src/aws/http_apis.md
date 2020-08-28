# HTTP APIs

When `instance.enable_api` in `hark.toml` is true, Hark configures a single API
gateway endpoint for all routes and methods.

It expects a function called `on_http` in the executable with the following
function signature:

```javascript
fn on_http(method, path, event) {
  // ...
}
```

- `method`: string (e.g. "GET", "POST")
- `path`: string (e.g. "/compute")
- `event`: dictionary (full AWS Lambda event, in [version 1.0 format][1])

[Source (HttpHandler)][2]

[1]: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
[2]: https://github.com/condense9/hark-lang/blob/master/src/hark_lang/run/lambda_handlers.py
