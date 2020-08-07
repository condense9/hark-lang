![Teal](doc/teal.png)

---

![Tests](https://github.com/condense9/teal-lang/workflows/Build/badge.svg?branch=master) [![PyPI](https://badge.fury.io/py/teal-lang.svg)](https://pypi.org/project/teal-lang) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380)

**The Teal Programming Language**

Teal hides the complexity of AWS Lambda + SQS, so you can build serverless data
workflows without managing infrastructure.

Describe your workflows in a *real programming language* with first-class
functions, concurrency, and native Python inter-op. Test end-to-end locally,
then deploy to serverless AWS infrastructure in under 60s and start workflows
from anything that can invoke Lambda.

Like AWS Step Functions but cheaper and much nicer to use (overheads: a little
Lambda runtime, and a DynamoDB for Teal state).

Like Serverless Framework, but handles runtime glue logic in addition to
deployment.

*Status*: Teal works well for small workflows: 5-10 Lambda invocations. Larger
workflows may cause problems, and there is a known issue caused by DynamoDB
restrictions ([#12](https://github.com/condense9/teal-lang/issues/12)).

<!-- As presented at PyCon Africa 2020. (Watch the presentation, or follow along with the examples). -->

<!-- Watch an introduction video. -->

[Get started in 2 minutes](#up-and-running-in-2-minutes).

[Read the documentation](https://teal-book.condense9.com).

[PyCon Africa 2020 Demos!](https://github.com/condense9/teal-demos).


## Contributing

Teal is growing rapidly, and contributions are [warmly welcomed](CONTRIBUTING.md).


## Is Teal for me?

Teal *is* for you if:
- You use Python for processing data, or writing business process workflows.
- You want an alternative to AWS Step Functions.
- You don't want to to deploy and manage a task platform (Airflow, Celery, etc).

**Data in**: You can invoke Teal like any Lambda function (AWS cli, S3 trigger,
API gateway, etc).

**Data out**: Use the Python libraries you already have for database access.
Teal just connects them together.

**Development**: Teal runs locally, so you can thoroughly test Teal programs
before deployment (using minio and localstack for any additional infrastructure
that your code uses.

**Operating**: Teal enables contextual cross-thread logging and stacktraces out
of the box, since the entire application is described in one place.

[Teal Cloud](https://condense9.com) (coming soon) will make this even easier,
with a graphical console, one-click rollbacks of entire serverless applications,
and more. Sign up to the mailing list to hear about this first:
[https://www.condense9.com/](https://www.condense9.com/).


| Teal is like...                     | But...                                                                                                        |
|-------------------------------------|---------------------------------------------------------------------------------------------------------------|
| AWS Step Functions                  | Teal programs aren't bound to AWS and don't use Step Functions under the hood (just plain Lambda + DynamoDB). |
| Orchestrators (Apache Airflow, etc) | You don't have to manage infrastructure, or think in terms of DAGs, and you can test everything locally.      |
| Task runners (Celery, etc)          | You don't have to manage infrastructure.                                                                      |
| Azure Durable Functions             | While powerful, Durable Functions (subjectively) feel complex - their behaviour isn't always obvious.         |


[Read more...](https://teal-book.condense9.com/why.html)


## Why should I learn a new language?

Because it'll give you a new way to *think* about cloud software.

Teal is not a Python replacement. It has one specific goal: eliminate the need
to *implement* infrastructure.

Writing your own infrastructure is like writing assembly code - only do it if
you really have extreme or unusual requirements. Otherwise, use a high-level
language (Teal!) that hides the complexity and compiles to "soft
infrastructure".


## Up and running in 2 minutes

All you need:
- An AWS account, and [AWS CLI](https://github.com/aws/aws-cli#getting-started)
  configured.
- A Python 3.8 virtual environment

Teal is built with Python, and distributed as a Python package. To install it,
run:

```shell
$ pip install teal-lang
```

This gives you the `teal` executable. Try `teal -h`.

Copy the following snippet into a file called `service.tl`:

```
// service.tl

fn main() {
  print("Hello World!");
}
```

Run it (`-f main` is optional, and `main` is the default):

```shell
~/new_project $> teal service.tl -f main
```

Initialise the project (required for deployment):

```shell
~/new_project $> teal init
```

And deploy the service to your AWS account (requires AWS credentials and
`AWS_DEFAULT_REGION` to be defined):

```shell
~/new_project $> teal deploy
```

Finally, invoke it in AWS (`-f main` is optional, as before):

```shell
~/new_project $> teal invoke -f main
```

That's it! You now have a Teal instance configured in your AWS account, built on
the AWS serverless platform (S3 + Lambda + DynamoDB). [More info...](https://teal-book.condense9.com/dev/aws.html)

Explore a more complex example: [Fractals](examples/fractals).

[Create an issue](https://github.com/condense9/teal-lang/issues) if none of this
makes sense, or you'd like help getting started.

Read more...
- [about the language](https://teal-book.condense9.com/language/index.html)
- [about the development process](https://teal-book.condense9.com/development/index.html)
- [about configuring Teal](https://teal-book.condense9.com/configuration.html)




## Things Teal can do

When running in AWS, Teal threads run in separate lambda invocations.

### Concurrency & Synchronisation

This is useful when a set computations are related, and must be kept together.

```javascript
/**
 * Return f(x) + g(x), computing f(x) and g(x) in parallel in two separate
 * threads (Lambda invocations in AWS).
 */
fn compute(x) {
  a = async f(x);     // Start computing f(x) in a new thread
  b = async g(x);     // Likewise with g(x)
  await a + await b;  // Stop this thread, and resume when {a, b} are ready
}
```

*Traditional approach*: Manually store intermediate results in an external
database, and build the synchronisation logic into the cloud functions `f` and
`g`, or use an orchestrator service.

[Read more...](https://teal-book.condense9.com/language/threads.html)


### Trivial Pipelines

Use this approach when each individual function may take several minutes (and
hence, together would break the 5 minute AWS Lambda limit).

```javascript
/**
 * Compute f(g(h(x))), using a separate lambda invocation for each
 * function call.
 */
fn pipeline(x) {
  a = async h(x);
  b = async g(await a);
  f(await b);
}
```

*Traditional approach:* This is functionally similar to a "chain" of AWS Lambda
functions and SQS queues.


### Mapping / reducing

Teal functions are first-class, and can be passed around (closures and anonymous
functions are planned, giving Teal object-oriented capabilities).

```javascript
/**
 * Compute [f(element) for element in x], using a separate lambda invocation for
 * each application of f.
 */
fn map(f, x, accumulator) {
  if nullp(x) {
    accumulator
  }
  else {
    // The Teal compiler has tail-recursion optimisation
    map(func, rest(x), append(accumulator, async f(first(x))))
  }
}
```

This could be used like:

```javascript
fn add2(x) {
  x + 2
}

fn main() {
  futures = map(add2, [1, 2, 3, 4], []);
  // ...
}
```

[Read more...](https://teal-book.condense9.com/language/functions.html)


## Notes about syntax

The syntax should look familiar, but there are a couple of things to point out.

### No 'return' statement

Every expression must return a value, so there is no `return` statement. The
last expression in a 'block' (expressions between `{` and `}`) is returned
implicitly.

```javascript
fn foo() {
  "something"
}

fn main() {
  print(foo())  // -> prints "something"
}
```

### Semi-colons are required...

... when there is more than one expression in a block.

This is ok:

```javascript
fn main() {
  print("done")
}
```

So is this:

```javascript
fn main() {
  print("one");
  print("two")
}
```

And this:

```javascript
fn main() {
  print("one");
  print("two");
}
```

But this is not ok:

```javascript
fn main() {
  print("one")  // <- missing semicolon!
  print("two")
}
```


### 'print' returns the value printed

In this snippet, "Hello Worlds!" is actually printed twice. First in `bar`, then
in `main`.

```javascript
fn bar() {
  print("Hello Worlds!")
}

fn main() {
  print(bar())
}
```

```shell
$> teal -q service.tl
Hello Worlds!
Hello Worlds!
```

### 'if' is an expression, and returns a value

Think about it like this: An `if` expression represents a choice between
*values*.

```javascript
v = if something { true_value } else { false_value };

// if 'something' is not true, v is set to null
v = if something { value };
```


## FAQ
<!-- NOTE: Taken from guide/src/why.md -->

**Why is this not a library/DSL in Python?**

When Teal threads wait on a Future, they stop completely. The Lambda function
saves the machine state and then terminates. When the Future resolves, the
resolving thread restarts any waiting threads by invoking new Lambdas to pick up
execution.

To achieve the same thing in Python, the framework would need to dump the entire
Python VM state to disk, and then reload it at a later point -- this may be
possible, but would certainly be non-trivial. An alternative approach would be
to build a langauge on top of Python that looked similar to Python, but felt
*wrong* because it was really faking things under the hood.

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

Teal is beta quality, which means that it's not thoroughly tested or feature
complete. This is a non-exhaustive list.

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


---

## About

Teal is maintained by [Condense9 Ltd.](https://www.condense9.com/). Get in touch
with [ric@condense9.com](ric@condense9.com) for help getting running, or if you
need enterprise deployment.

Teal started because we couldn't find any data engineering tools that were
productive and *felt* like software engineering. As an industry, we've spent
decades growing a wealth of computer science knowledge, but building data
pipelines in $IaC, or manually crafting workflow DAGs with $AutomationTool,
*just isn't software*.

## License

Apache License (Version 2.0). See [LICENSE](LICENSE) for details.

---

[![forthebadge](https://forthebadge.com/images/badges/gluten-free.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/built-with-love.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/check-it-out.svg)](https://forthebadge.com)

