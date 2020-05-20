# The Teal Programming Language

![Tests](https://github.com/condense9/teal-lang/workflows/Build/badge.svg?branch=master) [![PyPI](https://badge.fury.io/py/teal-lang.svg)](https://pypi.org/project/teal-lang)

Teal is a programming language for microservice orchestration.

It's for building applications with long-running tasks, like data (ETL)
pipelines, on top of the Python libraries you know and love.

Teal gives you:
- *really fast development* with **easy local testing**, and no coupling between
  application and infrastructure.
- cheap deployments, because **everything is serverless** and there is no
  orchestrator to run idle.
- built-in **tracing/profiling**, so it's easy to know what's happening in your
  workflows.

Documentation coming soon! For now, browse the [the examples](test/examples) or
the check out the [Teal Playground](https://www.condense9.com/playground).


## Getting started

**Teal is alpha quality - don't use it for mission critical things.**

```shell
$ pip install teal-lang
```

This gives you the `teal` executable.

Browse the [the examples](test/examples) to explore the syntax.

Check out an [example AWS deployment](examples/hello/serverless.yml) using the
Serverless Framework.

[Create an issue](https://github.com/condense9/teal-lang/issues) if none of this
makes sense, or you'd like help getting started.


### Teal May Not Be For You!

Teal *is* for you if:
- you want to build ETL pipelines *really quickly*.
- you have a repository of data processing scripts, and want to connect them
  together in the cloud.
- you insist on being able to test as much as possible locally.
- You don't have time (or inclination) to deploy and manage a full-blown
  platform (Spark, Airflow, etc).
- You're wary of Step Functions (and similar) because of vendor lock-in and cost.

Core principles guiding Teal design:
- Do the heavy-lifting in Python.
- Keep business logic out of infrastructure (no more hard-to-test logic defined
  in IaC, please).
- Workflows must be fully tested locally before deployment.


## Why Teal?

Teal is **not** Kubernetes, because it's not trying to let you easily scale
Dockerised services.

Teal is **not** containerisation, because.. well because there are no containers
here.

Teal is **not** a general-purpose programming language, because that would be
needlessly reinventing the wheel.

Teal is a very simple compiled language with only a few constructs:

1. named variables (data, functions)
2. `async`/`await` concurrency primitives 
3. Python (>=3.8) interop
4. A few basic types

Two runtimes have been implemented so far -- local and AWS Lambda, but there's
no reason Teal couldn't run on top of (for example) Kubernetes. [Issue
#8](https://github.com/condense9/teal-lang/issues/8)

**Concurrency**: Teal gives you "bare-metal concurrency" (i.e. without external
coordination) on top of AWS Lambda.

When you do `y = async f(x)`, Teal computes `f(x)` on a new Lambda instance. And
then when you do `await y`, the current Lambda function terminates, and
automatically continues when `y` is finished being computed. There's no idle
server time.

**Testing**: The local runtime lets you test your program before deployment, and
uses Python threading for concurrency.

**Tracing and profiling**: Teal has a built-in tracer tool, so it's easy to see
where the time is going.


## Current Limitations and Roadmap

Only one Teal program file is supported, but a module/package system is
[planned](https://github.com/condense9/teal-lang/issues/9).

There's no error handling - if your function fails, you'll have to restart the
whole process manually. An exception handling system is
[planned](https://github.com/condense9/teal-lang/issues/1).

Function inputs and outputs aren't typed. This is a limitation, and will be
fixed soon, probably using
[ProtoBufs](https://developers.google.com/protocol-buffers/) as the interface
definition language.

Currently you can only call Teal or Python functions -- arbitrary microservices
can't be called. Before Teal v1.0 is released, this will be possible. You will
be able to call a long-running third party service (e.g. an AWS ML service) as a
normal Teal function and `await` on the result.

Teal really should be able to natively manipulate JSON objects. This may happen
before v1.0.

---


## Contributing

Contributions of any form are welcome! The usual fork/PR approach is fine.


## Who?

Teal is maintained by [Condense9 Ltd.](https://www.condense9.com/), which is
really [one guy](https://www.linkedin.com/in/rmhsilva/) who loves maths and
programming languages.

Teal started because he couldn't find any data engineering tools that were
productive and *felt* like software engineering. As an industry, we've spent
decades growing a wealth of computer science knowledge, and building data
pipelines in $IaC, or manually crafting workflow DAGs with $AutomationTool, just
isn't software.


## License

Apache License (Version 2.0). See [LICENSE](LICENSE) for details.
