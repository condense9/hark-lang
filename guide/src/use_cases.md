# Cases for Teal


## Data pipelines



```javascript

```


## Background web tasks

Teal has basic support for API Gateway endpoints, which means you can trigger
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
