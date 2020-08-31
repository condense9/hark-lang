# Cases for Hark


## Data pipelines (workflows)

Hark was originally created for building serverless data pipelines, and this is
its primary use-case.

Here's an example of a task which
- is triggered on S3 upload
- solves an [embarassingly parallel][1] problem

```javascript
import(split_file, src, 2);
import(process_chunk, src, 1);
import(save_all, src, 1);

// bucket and key filter configured elsewhere (hark.toml)
fn on_upload(bucket, key) {
  chunks = split_file(bucket, key);
  results = map_async(process_chunk, chunks);
  save_all(results);
  print("Finished ᵔᴥᵔ");
}
```

Key points:

- Every chunk of the file will be processed by `process_chunk` in parallel
  (`map_async` defined elsewhere).

- While that happens, the Lambda running `on_upload` is completely stopped. So
  you don't waste computation time.

- You can run this program *locally* before deployment to test the logic. For
  example, what happens if `process_chunk` passes a bad value to `save_all`?
  It'll be much easier to debug that kind of situation locally than in the
  cloud!


[1]: https://en.wikipedia.org/wiki/Embarrassingly_parallel


## Background web tasks

Hark has basic support for API Gateway endpoints, which means you can trigger
long-running background tasks from your website frontend, and easily keep track
of when they complete.

```javascript
fn on_http(method, path, body, lambda_event) {
  if path == "/dump_data" {
    async dump_user_data(lambda_event);
    {"session_id": sid()};  // use the ID to check the dump status later
  }
  else if ...
}
```
