# The Teal Programming Language

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
