# The Hark Programming Language

Hark is a *functional*, *compiled* language which aims to support first-class
concurrency and mainstream language inter-op. It compiles into byte-code which
runs on [The Hark VM](/vm/index.html) .

Hark has:

1. Named variables.

2. Threads, and `async` & `await` primitives to manage them.

3. Python 3.8 interoperability ([Foreign Function Interface][1]).

4. JSON-compatible types (strings, numbers, lists, dictionaries).

5. First-class functions (proper closures coming soon).

The compiler is basic at the moment, but does feature tail-call optimisation for
recursive functions. Compile-time correctness checks (e.g. bound names, types,
etc) are planned.
