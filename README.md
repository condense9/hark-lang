# The Teal Programming Language

![Tests](https://github.com/condense9/teal-lang/workflows/Build/badge.svg?branch=master) [![PyPI](https://badge.fury.io/py/teal-lang.svg)](https://pypi.org/project/teal-lang) [![Gitter](https://badges.gitter.im/Teal-Lang/community.svg)](https://gitter.im/Teal-Lang/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

Teal is designed for passing data between Python functions running in the cloud
with very little infrastructure. It's like having a cluster, without having to
manage a cluster.

```javascript
// service.tl
import(read_items,     :python src.data_lib)
import(transform_item, :python src.data_lib)
import(get_metadata,   :python src.data_lib)
import(save_item,      :python src.data_lib)
import(aggregate,      :python src.data_lib)

fn handle(item) {
  // Get the metadata and do the transform in parallel
  metadata = async get_metadata(item)
  transformed = async transform_item(item)
  save_item(await metadata, await transformed)
}

fn main(items_csv) {
  items = read_items(items_csv)
  results = map(items, async handle)
  aggregate(map(results, await)) // wait for all handling to finish
  "done"
}
```

Run it locally:

```
$ teal service.tl test_items.csv
```

And deploy it to the cloud:

```shell
$ teal deploy
Teal: {"version": "0.2.1"}
Done (52s elapsed).

$ aws s3 cp test_items.csv s3://your-bucket teal
...

$ invoke -f main test_items.csv
```

---

## Introduction

Teal threads run in parallel on separate compute resource, and Teal handles data
transfer and synchronisation.

**Data in**: You can invoke Teal like any Lambda function (AWS cli, S3 trigger,
API gateway, etc).

**Data out**: Use the Python libraries you already have for database access.
Teal just connects them together.

**Testing**: There is a local runtime too, so you can thoroughly test Teal
programs before deployment (using minio and localstack for any additional
infrastructure that your code uses).

| Teal is like...                     | But...                                                                                                   |
|-------------------------------------|----------------------------------------------------------------------------------------------------------|
| AWS Step Functions                  | Teal programs can be tested locally, and aren't bound to AWS.                                            |
| Orchestrators (Apache Airflow, etc) | You don't have to manage infrastructure, or think in terms of DAGs, and you can test everything locally. |
| Task runners (Celery, etc)          | You don't have to manage infrastructure.                                                                 |
| Azure Durable Functions             | While powerful, Durable Functions (subjectively) feel complex - their behaviour isn't always obvious.    |

[Read more...](#why-teal)

Teal functions are like coroutines - they can be paused and resumed at any
point. Each horizontal bar in this plot is a separate Lambda invocation. Try
implementing that in Python. [Read more...](#faq)

![Concurrency](doc/functions.png)


## Getting started

```shell
$ pip install teal-lang
```

This gives you the `teal` executable - try `teal -h`.

Documentation is coming soon! For now, check out the [the Fractal
example](examples/fractals) or the
[Playground](https://www.teal-lang.org/playground).

[Create an issue](https://github.com/condense9/teal-lang/issues) if none of this
makes sense, or you'd like help getting started.


### Teal May Not Be For You!

Teal *is* for you if:
- you use Python for long-running tasks.
- you have an AWS account.
- you have a repository of data processing scripts, and want to run them
  together in the cloud.
- You don't have time (or inclination) to deploy and manage a full-blown task
  platform (Airflow, Celery, etc).
- You don't want to use AWS Step Functions .

Core principles guiding Teal design:
- Do the heavy-lifting in Python.
- Keep business logic out of infrastructure (no more hard-to-test logic defined
  in IaC, please).
- Workflows must be fully tested locally before deployment.


## Why Teal?

Teal is like AWS Step Functions, but is cheaper (pay only for the Lambda
invocations and process data), and way easier to program and test. The tradeoff
is you don't get tight integration with the AWS ecosystem (e.g. Teal doesn't
natively support timed triggers).

Teal is like Azure Durable Functions -- it lets you pause and resume workflows,
but it's (subjectively) nicer to write. The syntax feels natural. Also it's not
bound to Azure.

Teal is like a task runner (Celery, Apache Airflow, etc), but you don't have to
manage any infrastructure.

Teal is **not** Kubernetes, because it's not trying to let you easily scale
Dockerised services.

Teal is **not** a general-purpose programming language, because that would be
needlessly reinventing the wheel.

Teal is a simple compiled language with only a few constructs:

1. named variables
2. `async` & `await` concurrency primitives 
3. Python (>=3.8) interoperability (FFI)
4. A few basic types (strings, numbers, lists)
5. first-class functions (proper closures coming soon)

Two interpreters have been implemented so far -- local and AWS Lambda, but
there's no reason Teal couldn't run on top of (for example) Kubernetes. [Issue
#8](https://github.com/condense9/teal-lang/issues/8)

**Concurrency**: When you do `y = async f(x)`, `f(x)` is started on a new Lambda
instance. And then when you do `await y`, the current Lambda function
terminates, and automatically continues when `y` is finished being computed.

The compiler is basic at the moment, but does feature tail-call optimisation for
recursive functions. Compile-time correctness checks (e.g. bound names, types,
etc) are coming soon.


## FAQ

**Why is this not a library/DSL in Python?**

When Teal threads wait on a Future, they stop completely. The Lambda function
saves the machine state and then terminates. When the Future resolves, the
resolving thread restarts any waiting threads by invoking new Lambdas to pick up
execution.

To achieve the same thing in Python, the framework would need to dump the entire
Python VM state to disk, and then reload it at a later point -- I don't know
Python internals well enough to do this, and it felt like a huge task.

**How is Teal like Go?**

Goroutines are very lightweight, while Teal `async` functions are pretty heavy --
they involve creating a new Lambda (or process, when running locally).

Teal's concurrency model is similar to Go's, but channels are not fully
implemented so data can only be sent to/from a thread at call/return points.

**Is this an infrastructure-as-code tool?**

No, Teal does not do general-purpose infrastructure management. There are
already great tools to do that ([Terraform](https://www.terraform.io/),
[Pulumi](https://www.pulumi.com/), [Serverless
Framework](https://www.serverless.com/), etc).

Instead, Teal reduces the amount of infrastructure you need. Instead of a
distinct Lambda function for every piece of application logic, you only need the
core Teal interpreter (purely serverless) infrastructure.

Teal will happily manage that infrastructure for you (through `teal deploy` and
`teal destroy`), or you can set it up with your in-house custom system.


## Current Limitations and Roadmap

Teal is alpha quality, which means that it's not thoroughly tested, and lots of
breaking changes are planned. This is a non-exhaustive list.

### Libraries

Only one Teal program file is supported, but a module/package system is
[planned](https://github.com/condense9/teal-lang/issues/9).

### Error Handling

There's no error handling - if your function fails, you'll have to restart the
whole process manually. An exception handling system is
[planned](https://github.com/condense9/teal-lang/issues/1).

### Typing

Function inputs and outputs aren't typed. This is a limitation, and will be
fixed soon, probably using
[ProtoBufs](https://developers.google.com/protocol-buffers/) as the interface
definition language.

### Calling Arbitrary Services

Currently you can only call Teal or Python functions -- arbitrary microservices
can't be called. Before Teal v1.0 is released, this will be possible. You will
be able to call a long-running third party service (e.g. an AWS ML service) as a
normal Teal function and `await` on the result.

### Dictionary (associative map) primitives

Teal really should be able to natively manipulate JSON objects. This may happen
before v1.0.

---


## Contributing

Contributions of any form are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

Minimum requirements to develop:
- Docker (to run local DynamoDB instance)
- Poetry (deps)

Use `scripts/run_dynamodb_local.sh` to start the database and web UI. Export the
environment variables it gives you - these are required by the Teal runtime.


## About

Teal is maintained by [Condense9 Ltd.](https://www.condense9.com/). Get in touch
with [ric@condense9.com](ric@condense9.com) for bespoke data engineering and
other cloud software services.

Teal started because we couldn't find any data engineering tools that were
productive and *felt* like software engineering. As an industry, we've spent
decades growing a wealth of computer science knowledge, but building data
pipelines in $IaC, or manually crafting workflow DAGs with $AutomationTool,
*just isn't software*.


## License

Apache License (Version 2.0). See [LICENSE](LICENSE) for details.
