# From Source to Success

We'll begin by exploring the process of going from Hark source code to
successfully running a multi-thread process in AWS.

Here's our source:

```javascript
// service.hk
import(foo, pysrc, 1);

fn bar(x) {
  x + 1
}

fn compute(x) {
  a = async foo(x);
  b = bar(x);
  await a + b;
}

fn main() {
  compute(1)
}
```

Features:

- one imported Python function, `foo`
- two Hark functions, `bar` and `compute`
- each function takes 1 argument (assumed to be an `int`)
- `foo(x)` is called asynchronously (new thread)
- `bar(x)` is evaluated in the current thread
- `a` is waited for
- the sum `foo(x) + bar(x)` is returned

Here's the Python source:

```python
# pysrc/__init__.py

def foo(x):
    return x * 2
```

Running the program:

```shell
$ hark service.hk
4
```

Absolutely *breathtaking*.

Lots of things happened in the milliseconds it took to make that fantastic
number four appear in our console. Before anything particularly interesting
however, the Hark CLI tries to interpret our request.
