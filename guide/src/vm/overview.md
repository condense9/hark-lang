# Overview

Styling hints:
- Nouns in *Italics* (and capitalised).
- Adjectives/verbs in **bold**.
- Code in `monospace**.

**Terms**

*Session*: 1 or more Threads.

*Top Level Thread*: the thread that initiated the Session.

A *TlMachine* instance runs a single thread.

The *Entrypoint* is the function that kicks-off a Session. This might be
`main()`, or it might be some other specific handler.


## Standard Output

Standard output in Hark is a bit different from the usual.

Instead of modelling the output as a stream, each *Session* has a list of items
collectively called *Standard Output*. The items are tuples containing:

- a timestamp
- the originating thread
- a string

e.g.

```python
[
#  timestamp, thread, message
  (123523432, 0, "thread 0 says hi\n"),
  (123523438, 1, "thread 1 says hi\n"),
]
```

You write to standard output using the `print()` builtin function.


## Probes

Each *Thread* gets assigned a *Probe*, which records interesting events during
execution, and is useful for tracing/debugging.


## Stopping

A *Thread* is **stopped** if:
- it has run out of *Instructions* to execute (i.e. run out of call stack)
- an error occurs

It is called **finished** in the first case, and **broken** in the second.

A *Session* is **stopped** if all *Threads* in it are **stopped**.

Similarly, a *Session* can be **finished** or **broken**.


## Futures

Each *Thread* gets assigned a *Future* and an *Error*.

If the Thread **finishes**, then it **resolves** the Future with its result.

If it **breaks**, then the *Future* will never resolve, and *Error* will contain
information about the error, and a stack trace.

Either way, the Thread is **stopped**.


## Stack Traces

A *Stack Trace* is created when one or more fatal errors occur in a Session.

*Stack Traces* are directed acyclic graphs with a single "entry" node, and an
"exit" node for every error in the session. "Stack Trace" is a misnomer, since
they're not really stacks, but it's kept because people are familiar with the
concept.

The nodes in the graph are called *Activation Records*. Activation Records are
like "Stack Frames", but more general - stack frames are usually items in a
strictly last-in-first-out data structure (the stack), activation records just
represent a function call context. See [Activation
Records](https://wiki.c2.com/?ActivationRecord).

An *Activation Record* is created when a Function is called. They contain:

- The function parameters
- The call-site (pointer to return address in the exe code)
- A "pointer" to parent AR

If more than one Thread breaks in the same Session, their Stack Traces will
share at least one common node (the *Entrypoint*). But they might share more
than one! Graphically, the Stack Traces could be represented together, where the
shared nodes are drawn only once.

For example:

```
    C-D-!
   /
A-B-E-F-G-!
```

In this case, the letters represent activation records (function calls). There
are two threads, and errors ocurring in AR `D` and `G`. Logically, the functions
do share stack traces, and it makes sense to display this.

## Results & Return Values

TODO
