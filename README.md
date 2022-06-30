# The Hark Programming Language

![Tests](https://github.com/condense9/hark-lang/workflows/Build/badge.svg?branch=master) [![PyPI](https://badge.fury.io/py/hark-lang.svg)](https://pypi.org/project/hark-lang) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380)

Hark lets you quickly build serverless data pipelines without managing any
infrastructure.

Hark is for you if:
- You use AWS.
- You use Python for **data engineering** or business process pipelines.
- You don't want to manage a task platform (Airflow, Celery, etc).

Key features:
- First-class local testing (there's a local Hark runtime).
- Concurrency primitives for multi-threaded pipelines.
- Zero infrastructure management and minimal maintenance.

[Quick start: Build an AWS Lambda pipeline in 2 minutes](#up-and-running-in-2-minutes).

**Comparisons**:
- Like Apache Airflow, but without infrastructure to manage.
- Like AWS Step Functions but cloud-portable and locally testable.
- Like Serverless Framework, but handles runtime glue logic in addition to
  deployment.

*Status*: Hark works well for small workflows: 5-10 Lambda invocations. Larger
workflows may cause problems, and there is a known issue caused by DynamoDB
restrictions ([#12](https://github.com/condense9/hark-lang/issues/12)).

<!-- Watch an introduction video. -->

[Documentation](https://guide.condense9.com).

Hark was Presented at PyCon Africa 2020. [Watch the presentation][pycon], or
[check out the demos][demos].

[demos]: https://github.com/condense9/hark-demos
[pycon]: https://www.youtube.com/watch?v=I8VGfOBzmF4


## Contributing

Hark is growing rapidly, and contributions are [welcome](CONTRIBUTING.md).


## Is Hark for me?

Hark *is* for you if:
- Your data is in AWS
- You use Python for processing data, or writing business process workflows.
- You don't want to deploy and manage a task platform (Airflow, Celery, etc).

**Data in**: You can invoke Hark like any Lambda function (AWS cli, S3 trigger,
API gateway, etc).

**Data out**: Use the Python libraries you already have for database access.
Hark just connects them together.

**Development**: Hark runs locally, so you can thoroughly test Hark programs
before deployment (using minio and localstack for any additional infrastructure
that your code uses.

**Operating**: Hark enables contextual cross-thread logging and stacktraces out
of the box, since the entire application is described in one place.

| Hark is like...                 | But...                                                                                                        |
|-------------------------------------|---------------------------------------------------------------------------------------------------------------|
| AWS Step Functions                  | Hark programs aren't bound to AWS and don't use Step Functions under the hood (just plain Lambda + DynamoDB). |
| Orchestrators (Apache Airflow, etc) | You don't have to manage infrastructure, or think in terms of DAGs, and you can test everything locally.      |
| Task runners (Celery, etc)          | You don't have to manage infrastructure.                                                                      |
| Azure Durable Functions             | While powerful, Durable Functions (subjectively) feel complex - their behaviour isn't always obvious.         |


[Read more...](https://guide.condense9.com/why.html)


## The 2 minute pipeline

All you need:
- An AWS account, and [AWS CLI](https://github.com/aws/aws-cli#getting-started)
  configured.
- A Python 3.8 virtual environment

Hark is built with Python, and distributed as a Python package. To install it,
run in a new virtualenv:

```shell
pip install hark-lang
```

This gives you the `hark` executable. Try `hark -h`.

Initialise the project with a few template files:

```shell
hark init
```

Copy the following snippet into `service.hk`:

```javascript
// Import the processing functions defined in Python
import(process_video_step1, src.video, 2);
import(process_video_step2, src.video, 3);
import(process_video_step3, src.video, 3);
import(process_video_final_step, src.video, 3);

// Process a named file
fn process_csv(key) {
  a = async process_video_step1(bucket, key);
  b = async process_video_step2(bucket, key, await a);
  c = async process_video_step3(bucket, key, await b);
  process_video_final_step(bucket, key, await c);
}
```

Run it locally to test:

```shell
hark service.hk -f on_upload filename.csv
```

And deploy the service to your AWS account (requires AWS credentials and
`AWS_DEFAULT_REGION` to be defined):

```shell
hark deploy
```

[Read more](https://guide.condense9.com/aws.html) about what this actually
creates.

Finally, invoke it in AWS (`-f main` is optional, as before):

```shell
hark invoke -f main your_bucket filename.csv
```

Read more...
- [about the language](https://guide.condense9.com/language/index.html)
- [about the development process](https://guide.condense9.com/development/index.html)
- [about configuring Hark](https://guide.condense9.com/configuration.html)


## Language Features

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

[Read more...](https://guide.condense9.com/language/threads.html)


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

Hark functions are first-class, and can be passed around (closures and anonymous
functions are planned, giving Hark object-oriented capabilities).

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
    // The Hark compiler has tail-recursion optimisation
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

[Read more...](https://guide.condense9.com/language/functions.html)


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
$> hark -q service.hk
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

When Hark threads wait on a Future, they stop completely. The Lambda function
saves the machine state and then terminates. When the Future resolves, the
resolving thread restarts any waiting threads by invoking new Lambdas to pick up
execution.

To achieve the same thing in Python, the framework would need to dump the entire
Python VM state to disk, and then reload it at a later point -- this may be
possible, but would certainly be non-trivial. An alternative approach would be
to build a langauge on top of Python that looked similar to Python, but hark
*wrong* because it was really faking things under the hood.

**How is Hark like Go?**

Goroutines are very lightweight, while Hark `async` functions are pretty heavy --
they involve creating a new Lambda (or process, when running locally).

Hark's concurrency model is similar to Go's, but channels are not fully
implemented so data can only be sent to/from a thread at call/return points.

**Is this an infrastructure-as-code tool?**

No, Hark does not do general-purpose infrastructure management. There are
already great tools to do that ([Terraform](https://www.terraform.io/),
[Pulumi](https://www.pulumi.com/), [Serverless
Framework](https://www.serverless.com/), etc).

Instead, Hark reduces the amount of infrastructure you need. Instead of a
distinct Lambda function for every piece of application logic, you only need the
core Hark interpreter (purely serverless) infrastructure.

Hark will happily manage that infrastructure for you (through `hark deploy` and
`hark destroy`), or you can set it up with your in-house custom system.


## Current Limitations and Roadmap

Hark is beta quality, which means that it's not thoroughly tested or feature
complete. This is a non-exhaustive list.

### Libraries

Only one Hark program file is supported, but a module/package system is
[planned](https://github.com/condense9/hark-lang/issues/9).

### Error Handling

There's no error handling - if your function fails, you'll have to restart the
whole process manually. An exception handling system is
[planned](https://github.com/condense9/hark-lang/issues/1).

### Typing

Function inputs and outputs aren't typed. This is a limitation, and will be
fixed soon, probably using
[ProtoBufs](https://developers.google.com/protocol-buffers) as the interface
definition language.

### Calling Arbitrary Services

Currently you can only call Hark or Python functions -- arbitrary microservices
can't be called. Before Hark v1.0 is released, this will be possible. You will
be able to call a long-running third party service (e.g. an AWS ML service) as a
normal Hark function and `await` on the result.


---

## About

Hark started because we couldn't find any data engineering tools that were
productive and *feel* like software engineering. As an industry, we've spent
decades growing a wealth of computer science knowledge, but building data
pipelines in $IaC, or manually crafting workflow DAGs with $AutomationTool,
feels more like hardware than software.


## License

Apache License (Version 2.0). See [LICENSE](LICENSE) for details.

---

[![forthebadge](https://forthebadge.com/images/badges/gluten-free.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/built-with-love.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/check-it-out.svg)](https://forthebadge.com)

The end. Here's a spaceship. Hacks and glory await.

```


                     `. ___
                    __,' __`.                _..----....____
        __...--.'``;.   ,.   ;``--..__     .'    ,-._    _.-'
  _..-''-------'   `'   `'   `'     O ``-''._   (,;') _,'
,'________________                          \`-._`-','
 `._              ```````````------...___   '-.._'-:
    ```--.._      ,.                     ````--...__\-.
            `.--. `-`                       ____    |  |`
              `. `.                       ,'`````.  ;  ;`
                `._`.        __________   `.      \'__/`
                   `-:._____/______/___/____`.     \  `
                               |       `._    `.    \
                               `._________`-.   `.   `.___
                                             SSt  `------'`
```


