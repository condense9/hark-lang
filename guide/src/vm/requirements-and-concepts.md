# Requirements and concepts

The Hark VM is designed to meet these requirements.

### 1. More than one thread

It must be possible to do more than one thing at a time. It must support
concurrency.

Corrolaries:
- There must be a way to pass data between threads.
- There must be a way to synchronise threads.

### 2. "Pause-able"

It must be possible to "pause" threads, and "continue" them when the data they
need is ready. While paused, it must be possible to easily and efficiently save
the state of a thread, and restore it upon continuation.

### 3. Symbolic data

It must be possible to define named values, and operate on them (functions and
variables).

### 4. Inter-op with other languages (FFI)

It must be possible to call Python functions (and possibly later - other
languages).

### 5. Portable

It must be a relatively simple job to port the VM to a new (cloud) platform.
Programs written in Hark should run the same on any implementation (ignoring the
effect of any Python calls).


## What are the core components?

These are the core components that make up the design. Understand these, and how
they interact, and you'll understand Hark.


### Threads

A Hark program starts off as a single thread, and can create other threads to
execute in parallel. Each thread begins executing from a specific function
(called its entrypoint).

Each thread executes instructions in *series* until it cannot return anymore (ie
it returns from its entrypoint). All threads share the same executable -- the
currently-implemented synchronisation method depend on it!

Each thread has:

- (one) *private* **data stack**
- (one) *private* **instruction pointer**
- (one) *shared* **Future**
- (many) *shared* **Activation Records**

### Executable

The executable is a **static** (does not change at run-time) data structure
containing:

- a set of function names
- a list of VM instructions and operands for each function
- debug data

*Note*: At the moment, the executable does not contain a "data" section, or any
globally named (non-function) values.

### Data Stack and Instruction Pointer

Within the context of a single thread, the Hark VM is a simple stack-based
machine (similar, in a distant way, [to Java's JVM][jvm]).

The instruction pointer is an index into the executable code, determining the
*next* instruction to be executed (it is pre-incremented).

The data stack supports basic push/pop semantics and can store any Hark
data-type, although this might change before Hark v1.0 to support proper heap
storage of data.

[jvm]: https://www.jopdesign.com/doc/stack.pdf

### Instructions

The VM operates like a traditional CPU -- by iterating over a list of
"instructions", and executing each one in the context of the current data stack.
Each instruction may pop or push data onto or from the stack.

Some special instructions exist in order to, for example:
- call foreign functions
- enable program control flow (ie, jumps)
- control the VM (pause a thread, write to standard output, etc) 

Instructions can take (fixed) operands.

### Activation Record

Activation records store the context of a function call (arguments, caller
activation record, return instruction address, etc). A bit like stack frames.
Stack frames are just activation records that maintain strict LIFO semantics,
hence the "stack" name.

[The C2 Wiki explains it well.](https://wiki.c2.com/?ActivationRecord)

Hark activation records do **not** have to maintain strict LIFO semantics, and
so they are not called stack frames. This makes it easier to support:
- closures
- cross-thread stack-traces.

### Futures

Each thread is associated with a single Future object. Futures can be
**resolved** or not. If they are resolved, they have an associated **value**. If
they are not resolved, they have a (possibly empty) list of **continuations**,
each of which represent the state of a paused thread.

When a thread returns from its entrypoint function, the associated Future is
resolved to the function's return value (top item on the data stack).

### Calling convention

The "calling convention" dictates how parameters are passed to functions and
results are returned. Normally (e.g. on Intel x86 processors), this would
involve registers. There are no data registers in the Hark VM, so the calling
convention here is very simple:

- push parameters onto the stack (reverse order)
- call function
- top item on the stack is the function's return value


### Key Abstraction 1: Storage

This is the "long-term" storage that any processor needs. The Hark VM abstracts
this so that storage backends are portable.


### Key Abstraction 2: Invocation

The Hark VM abstracts the creation of threads so that execution backends are
portable.
