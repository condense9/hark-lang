## C9C :: Condense9 Compiler

Goal, **PART ONE**:
- write concurrent programs and have them execute on serverless infrastructure

How:
- automate the plumbing (passing data between functions, synchronisation of
  threads, etc)

What this is:
- an abstract imperative machine with native concurrency
- a high-level language to express concurrent computation
- a compiler

Sort of like programming a cluster, but without the cluster part.

Goal, **PART TWO**:
- build serverless applications without knowing in detail how to configure
  AWS/GCP/etc

How:
- "synthesize" the infrastructure based on the logic description

What this is:
- enhancements to the language of part 1 to describe application requirements
- a transformer from the DAG in part 1 to an infrastructure description

Generating IAC.

The source language may include features like specifying performance/placement
requirements, and creating event handlers (e.g. this is a GET handler, and must
respond within 20ms).


### MVP Requirements

Build, deploy and run:
- data workflows
- simple web applications

Infrastructure generation:
- lambda functions
- SNS/SQS (inter-lambda communication)
- API Gateway endpoints (simple GET/POST requests for now)
- S3 bucket (object store)
- DynamoDB databases (key-value store)
- CDN (static content)


### Development rules

If it doesn't have a test, it doesn't exist.

If the tests don't pass, don't merge it.

If it's in scratch, it doesn't exist.

Format Python with [Black](https://pypi.org/project/black/).

Run [Shellcheck](https://www.shellcheck.net/) over shell scripts.

Use Python 3.8.


### Implementation Notes

It would be nice to have a consistent API to talk to infrastructure providers,
cross cloud. [Libcloud](https://libcloud.apache.org/ ) doesn't do Lambda,
unfortunately. But surely something else does. Ultimately though, it must be
possible for the programmer/designer to override the output.


## Software Design

The core "feature" is a functional-style language (embedded in Python) with
which the programmer describes their application, and a compiler for this
language.

For now, it's called C9. Totally unrelated to C, the language. And the compiler
is, of course, called C9C (the Condense9 Compiler).

"C9 Service Object" (.cso) files are packages that contain everything necessary
to deploy a service, *and* to interface with other services. A CSO is created
with `c9c service.py -o service.cso`, where service.py contains the
implementation. This may be split across multiple files, using Python's normal
module import mechanisms.

CSOs are sort of like DLLs, or object files - they contain the executable code,
but also list the symbols available, so that objects can be linked together.

There's no "linker" in the cloud, but we do need to know what a service can do.
So a CSO is a tuple:

CSO :: (options, outputs, methods, events, infrastructure)

Options: values that may/must be provided at deploy time (e.g. a foreign DB).

Outputs: values that will be readable in the service when it's deployed.

Methods: methods that can be called (with parameters) when the service is
deployed.

Events: events which other services can subscribe to.

Infrastructure: partially configured IAC (may take values from Options) to run
this service.


### Part 1 - concurrent functional programming

DAG -> User code + "in/out runtime"

Writing one lambda function is fairly easy, and there are many tools that make
dev/test/deployment easy. Writing multiple lambdas that interact with each other
is much harder. AWS Step functions (basically state machines) is the only tool
we know of that make this a bit easier.

The main idea of C9 is to use traditional programming methods to express the
interaction. Specifically, functional composition - calling functions, passing
the results to other functions.

C9 is able to call "foreign" functions (ie normal Python functions) which can do
anything they like. These are the "tasks". They may have defined input/output
types. They can be connected together using the C9 language.

Part 1 of the compiler takes the C9 DAG and produces a single "runtime" package
that wraps all of the user tasks. This package can be run on any platform that
implements the runtime - currently local and AWS.

Only a single Lambda function is required, with a single input/output SNS
topic - the runtime determines which code to run. If it's easier for metrics, we
could deploy one lambda per task, but it's not technically necessary.


### Part 2 - infrastructure generation

DAG + constraints -> infrastructure as code

Designing infrastructure is hard, but very repetitive - most applications will
look very similar (object store, database, computation, api, ...), although the
configuration details may well vary.

Most of those details can be inferred from the DAG, and the compiler can choose
the best configurations based on constraints defined by the programmer (e.g.
cost, response time, regions...).

The challenge is how to break up the DAG - what's the smallest element?

Since service objects specify 

Buckets - can be inferred as a 
