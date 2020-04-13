# The C9 Machine

The C9 machine (C9M) is a very simple single-threaded virtual stack machine.
However, there can be multiple machines running concurrently, using
[Future-like](https://en.wikipedia.org/wiki/Futures_and_promises)) objects to
pass data around and synchronise.

## Primitive Data Types

Only
- strings
- numbers
- lists

Not much? Nope. Enough to do simple things, and more complex things should be
done with Foreign functions for now.


## Instructions Reference

You probably don't need this.

### `Call`

Operands:
- `int` (number of arguments the function takes)

Synchronous function calls. As expected, call the specified function with the
given number of arguments popped from the stack, and push the result. The
function will run to completion on the current machine.

### `ACall`

Operands:
- `int` (number of arguments the function takes)

Asynchronous function calls. Spin up a new machine to execute the given
function. The specified number of values are removed from the stack, replaced
with a Future, and execution carries on immediately.

### `Wait`

Operands
- `int` (offset of value in the stack to wait for)

If the value at the specified offset in the stack is a Future, and it hasn't
resovled, the current machine will halt, and a continuation for that future is
stored. When the future resolves, execution continues.

### `MFCall`

Operands
- `callable` (the Python function to call)
- `int` (number of arguments it takes)

Call a Python function with the given number of arguments popped from the stack,
and push the result.

### ... and more!
