# Introduction

C9 is a functional language, embedded in Python, to describe:

- Nested (and concurrent) calls to serverless functions
- High-level infrastructure dependencies (IAC)

It is *compiled* to produce code which runs on the C9 virtual machine, and, from
the same program, infrastructure-as-code is *synthesised*.

The VM has two implementations:

- "Native" (local), using Python threads for concurrency, intended for testing
- AWS, using asynchronous AWS Lambda invocations for concurrency

C9 is not a good choice (at the moment) for general purpose simple APIs that can
be entirely handled by a single function. There's too much overhead in the glue
logic.

It's great for describing more complex computation or data processing that is
time-consuming and composed of many functions. These functions may call each
other, may run concurrently, and may need to be synchronised to provide a result
somewhere.

C9 is intended to save time in design and deployment. It sits alongside
Infrastructure-As-Code tools such as Terraform, and orchestration/clusterisation
tools such as Kubernetes.
