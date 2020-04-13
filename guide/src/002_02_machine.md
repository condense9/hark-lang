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

Lists are made up of "Atoms" and other lists. Anything that isn't a list is an
Atom. For example, `1` is an atom, and so is `"hello world"`, but `[1, "hello
world"]` is of course a list.


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


### `Eq`

Removes two items from the stack and pushes `True` onto the stack if they're
equal, `False` otherwise.

### `Atomp`

Replace the top item of the stack with `True` if it is an Atom (i.e., anything
other than a list).

### `Nullp`

Replace the top item of the stack with `True` if it is Null (a list of length
0).

### `Cons`

Take the top two items (a, b) off the stack and replace them with something
according to the following:

```
 a,   [b]  -> [a, b]   -- a is an atom, b is a list
 a,    b   -> [a, b]   -- a and b are both atoms
 otherwise -> error    
```

This allows us to do list construction. NOTE that the last rule implies we can
only construct lists one level deep. This is a known bug and will be fixed ;).

### `First`

Pop the top item off the stack, assume it's a list, and push just the first
element from it.

This, along with `Rest` allow us to do arbitrary list deconstruction.

### `Rest`

Pop the top item off the stack, assume it's a list, and push everything except
the first element.


### ... and more!
