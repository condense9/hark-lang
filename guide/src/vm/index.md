# The Teal VM

Teal ([the language](/language/index.html)) compiles into byte-code that runs on
a virtual machine designed for *concurrency* and *portability*.

**Concurrency**: When you do `y = async f(x)`, `f(x)` is started on a new Lambda
instance. And then when you do `await y`, the current Lambda function
terminates, and automatically continues when `y` is finished being computed.

  **Portability**: Two implementations of this VM exist so far—local and AWS
Lambda, but there's no reason Teal couldn't run on top of (for example)
Kubernetes ([See Issue #8][2]).

## Abstractions

At its core, the VM has two abstractions:

- Storage: what does it mean to store/retrieve a value? For example, this is
  done with DynamoDB in AWS.

- Invocation: what does it mean to "invoke" a function? In AWS, this is
  currently done with Lambda.
  
These are both *run-time* abstractions, but which could be guided by
compile-time source-code annotations. For example, if some functions have very
high memory requirements, the VM can happily invoke them on an appropriate
instance, while invoking other functions in a smaller instance.

Implement both of these, and you can run Teal.

Here's the current implementation landscape.

| Storage   | Invocation      | Platform | Notes                                          |
|-----------|-----------------|----------|------------------------------------------------|
| In-memory | threading       | Local    | Python threads are not actually concurrent!    |
| DynamoDB  | threading       | Local    | Only useful for testing the DynamoDB storage.  |
| DynamoDB  | multiprocessing | Local    | Concurrent. Use DynamoDB Local.                |
| DynamoDB  | Lambda          | AWS      | Concurrent. Limitations on DynamoDB item size! |



[1]: https://en.wikipedia.org/wiki/Foreign_function_interface
[2]: https://github.com/condense9/teal-lang/issues/8
