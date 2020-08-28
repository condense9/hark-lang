# Why Hark?

Hark is not a replacement for your favourite mainstream language. It does
something new: eliminates the *need* to write infrastructure.

Serverless applications are inherently distributed, and building distributed
systems by hand is hard. It's much easier to think about them as monolithic
applications which are then *compiled into* distributed applications.

Hark lets you do that. Some benefits:

- **Local testing**. Full local testing of the application *logic* (you still
  have to mock out third party services.

- **Advanced metrics**. Automatic log aggregation (like structured logging),
  making for much easier contextual debugging. Deep insight into application
  performance and cost (way better than the context-free AWS reporting).

- **Deployment**. Trivial deployment or rollback of entire applications, not
  just single functions.

- **Portability**. Hark is naturally cloud-agnostic. Only the AWS runtime has
been implemented so far, but in principle, Hark programs are fully portable
across execution environments.


## Soft infrastructure

*Don't write infrastructure when you want to write software.*

No one writes assembly code anymore. Infrastructure is a bit like assembly.

Most infrastructure patterns are repeatable, and can be described in simple
terms&mdash;"send outputs from here to there", or, "this function needs to
respond within 30ms to millions of messages concurrently".

Most of those patterns correspond to familiar software concepts&mdash;value
assignment, function calls and concurrency.

Instead of writing infrastructure, write software that gets compiled and *uses*
serverless infrastructure to get all the benefits, but doesn't expose the
complexity.

Using Hark means you get a solid, infrequently changing, and well-understood
infrastructure platform, rather than manually wiring together complicated
flow-charts yourself.


## Other approaches

Hark was originally created for building serverless data pipelines, and this is
its primary use-case. There are a couple of common ways to process data in AWS.

Here's how Hark stacks up.

| Method                                 | Fully Serverless? | Familiar programming model?                 | Local testing possible? | Setup time    |
|----------------------------------------|-------------------|---------------------------------------------|-------------------------|---------------|
| Large EC2 instance                     | No                | *Yes*                                       | *Yes*                   |               |
| Workflow managers (Apache Airflow etc) | No                | No (usually a "DAG" model)                  | *Yes* (docker image)    |               |
| Task runners (Celery, CI tools)        | No                | *Yes* (usually a simple API)                | *Yes*                   |               |
| AWS Step Functions                     | *Yes*             | No (flow-chart model)                       | *Yes* (docker image)    |               |
| DIY: Lambda + SQS + custom logic       | *Yes*             | *Yes*, but *lots* of AWS to learn           | Tricky (localstack...)  | Hours to days |
|                                        |                   |                                             |                         |               |
| Hark                                   | *Yes*             | *Yes* (new language, but familiar concepts) | *Yes* (built-in)        | 60s           |

Hark is like AWS Step Functions, but is cheaper (pay only for the Lambda
invocations and process data), and way easier to program and test. The tradeoff
is you don't get tight integration with the AWS ecosystem (e.g. Hark doesn't
natively support timed triggers).

Hark is like Azure Durable Functions -- it lets you pause and resume workflows,
but it's (subjectively) nicer to write. The syntax feels natural. Also it's not
bound to Azure.

Hark is like a task runner (Celery, Apache Airflow, etc), but you don't have to
manage any infrastructure.

Hark is **not** Kubernetes, because it's not trying to let you easily scale
Dockerised services.

Hark is **not** a general-purpose programming language, because that would be
needlessly reinventing the wheel.


## FAQ

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
