# Language Reference

Here is a C9 function called `process`:

```python
@Func
def process(obj):
    metadata = get_metadata(obj)
    chunks = get_chunks(obj)
    results = Map(process_chunk, chunks)
    return If(Null(results),
              False,
              save_to_db(metadata, results))
```

It takes an argument, `obj`, extracts some metadata and some "chunks" of data,
processes those chunks, and saves the results to a database.

C9 primitives come in three shapes:
- decorators
- keywords
- data types

There's also a standard library of useful things.

In C9, all primitives are capitalised.


## Decorators

### `@Func`

This declares that the decorated function is a C9 function, and *not Python*.

The important thing to remember is that in a C9 function, you can **only** use
C9 primitives or other C9 functions -- you can't call python functions. The
`process` function is only valid C9 if the functions it refers to
(`get_metadata`, `get_chunks`, ...) are also C9 functions.

So, for example, this is valid, though extremely boring:

```python
@Func
def foo(x):
    return x

@Func
def bar(x):
    return foo(x)
```

Mainly showing `foo` can be called directly from `bar`.


### `@Foreign`

This declares that the decorated function is a *Python* that is *callable* from
any C9 function. This is mostly syntax sugar for the *ForeignCall* keyword
(below**.

**Rule:** Only positional arguments are allowed -- no varargs, keyword args
(*yet!)

This is more interesting.

```python
@Foreign
def do_something(image_data):
    # do things with numpy ... 
    
@Func
def read_image(image_name):
    # ...

@Func
def main(image_name):
    image = read_image(image_name)
    return do_something(image)
```


### `@AsyncFunc`

Just like `Func`, but the resulting function will run asynchronously, returning
a Future object. The resulting Future can be passed around and used as an
argument to other functions.


### `@AsyncForeign`

Similary, declare a foreign function which will be executed asynchronously.


## Keywords

There are not many! There are two "kinds".

Compiler keywords (`import c9.lang`):

- If
- Quote
- Funcall
- ForeignCall
- Do
- Asm

Built-in machine instructions (`import c9.stdlib`):

- Wait
- Eq
- Atomp
- Nullp
- Cons
- First
- Rest

The difference is that the second keywords compile directly into the machine
instruction of the same name, while the first don't. That's not really important
though, you can treat them the same.


### `If`

```python
a = If(cond, then_value, else_value)
```

The value of a will be `then_value` if `cond` is **equal** to `True` (the Python
`True`), and will be `else_value` otherwise.


### `Funcall`

```python
a = Funcall(foo, 1, 2, blocking=True)
```

Call function `foo` with arguments `[1, 2]` and run it synchronously (blocking
-- i.e., wait until it finishes before proceeding).

```python
b = Funcall(bar, 1, 2, 3, blocking=False)
```

Call `bar` with `[1, 2, 3]` and run it asynchronously, getting a Future and
continuing immediately.

In both of these cases, the decorators above give us syntax sugar which allow us
to simply write:

```python
a = foo(1, 2)
b = bar(1, 2, 3)
```

Assuming `foo` and `bar` have been decorated with `Func` and `AsyncFunc`.

### `ForeignCall`

```python
a = ForeignCall(do_stuff, 1, 2)
```

Call the Python function `do_stuff`. If `do_stuff` has been decorated with
`@Foreign`, this could also be written:

```python
a = do_stuff(1, 2)
```

### `Do`

```python
a = Do(foo(1),
       bar(2),
       something(3),
       ...)
```

Evaluate an arbitrarily number of sub-expressions, assigning the result of the
*last-one* to `a`.

### `Quote`

```python
a = Quote(1)
```

This is slightly special -- it assigns the value of `a` to be the *literal*
value `1`. This is important because not all Python values have literal
equivalents in the C9 machine (C9M only implements a few data types...).

Syntax sugar exists, the following line is equivalent to the above.

```python
a = 1
```


### `Asm`

Write some raw assembly/machine code for the C9 Machine!

```python
Asm([a, b], [machine.Eq()])
```

"Capture" the values of `a` and `b`, and call the `Eq` machine instruction
(assuming you've imported the `machine` module).

The above is actually the definition of the `Eq` keyword in the C9 stdlib, and
so is equivalent to:

```python
Eq(a, b)
```

