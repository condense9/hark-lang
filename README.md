## C9C :: Condense9 Compiler

The instruction set, compiler and reference implementation of the abstract
machine.

Goal:
- write concurrent programs and have them execute on serverless infrastructure

How:
- automate the plumbing (passing data between functions, synchronisation of threads, etc)

What this is:
- an abstract imperative machine with native concurrency, and other
  cloud/serverless features*
- a high-level language to express concurrent computation, and other
  cloud/serverless features*
- a compiler

Sort of like programming a cluster, but without the cluster part.

*: Other features like specifying performance/placement constraints, and
creating event handlers (e.g. this is a GET handler, and must respond within
20ms)



### Capabilities

### Requirements
