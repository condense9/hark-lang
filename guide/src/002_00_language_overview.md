# Language Overview

There are four important parts to C9:
- The language
- The virtual machine
- The compiler
- The synthesiser

References to "C9" usually mean "C9, the language".

C9 is a *very* minimal functional language, which means functions are
first-class and are the primary method of writing programs. It's embebbded in
Python, but it is not Python! Concurrency is first-class and exposed as
async/await (although often it's implicit). The compiler takes a set of C9
functions and spits out sequences of instructions for the C9 virtual machine.

In C9, cloud infrastructure is first class.

Infrastructure can be created, and passed around, and the C9 synthesiser
determines (based on the C9 program), what infrastructure needs to be created,
and which functions need access to it.

However, because C9 is super-minimal, you can't actually do much useful with it.
So it has a built-in [foreign function
interface](https://en.wikipedia.org/wiki/Foreign_function_interface), letting
you implement the heavy lifting in your language of choice (currently only the
Python FFI is implemented...).
