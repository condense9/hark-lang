# File uploads

When `instance.upload_triggers` in `hark.toml` is configured, Hark enables file
upload triggering.

It expects a function called `on_upload` in the executable with the following
function signature:

```javascript
fn on_upload(bucket, key) {
  // ...
}
```

- `bucket`: string
- `key`: string


[Source (S3Handler)][1]

[1]: https://github.com/condense9/hark-lang/blob/master/src/hark_lang/run/lambda_handlers.py
