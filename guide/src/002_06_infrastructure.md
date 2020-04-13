# Infrastructure

C9 Handlers can have infrastructure attached to them, either explicitly or
implicitly. In the first case, a Python object representing the infrastructure
is created and used as an argument to a function. In the second case, the
infrastructure is attached to the function by a decorator, which may actually
attach more than one kind of infrastructure.

So you can represent abstract things like "authentication", or "REST API
endpoints" with decorators, and not worry about the details of what
infrastructure is actually required. 

Alternatively, you can instantiate exactly which infrastructure you want, and
pass them in to your functions.

The C9 compiler and synthesiser pick up both cases and resolve the dependencies
(i.e., figures out what actual cloud infrastructure needs to exist to make your
program work).


## Explicit Infrastructure

### `ObjectStore`

```python
bucket = ObjectStore("uploads")

@Func
def foo(x):
    do_something(bucket, x)
    
@Foreign
do_something(the_bucket, the_thing):
    # ...
```

Create an object store named "uploads".

When `do_something` is called at run-time (as it's a Foreign function),
`the_bucket` is an object containing information about the actual object store
infrastructure (e.g. the AWS ARN).


### `KeyValueStore`

```python
table = KVStore("table_name", attrs=dict(id="S"), keys=dict(id="HASH"))
```

A key-value store, based on a [DynamoDB
Table](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.create_table).


## Implicit Infrastructure

Usually you won't need to create these manually - they're added by decorators in
[Events](002_05_events.html).

### `HttpEndpoint`

One of this is added to a Function by the
[@HttpHandler](002_05_events.html#httphandler) decorator.

