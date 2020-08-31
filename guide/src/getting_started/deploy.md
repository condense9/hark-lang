# Deploy something!

We'll now build a slightly bigger program and run it on AWS. This time, there is
Hark and Python, and multiple threads.

In a fresh directory, create the bare minimum files for a new project:

```shell
$ hark init
```


### Source code

Add some complicated Python:

```python
# src/__init__.py

def complicated_stuff(x):
    print(f"Complicated! {x}")
    return x * 10
```

And some Hark:

```javascript
// service.hk
import(complicated_stuff, src, 1);

fn map(func, items, acc) {
  if nullp(items) {
    acc
  }
  else {
    map(func, rest(items), append(acc, func(first(items))))
  }
}

fn wait(item) {
  await item;
}

fn complicated(x) {
  async complicated_stuff(x);
}

fn main() {
  results = map(complicated, [1, 2, 3, 4, 5], []);
  map(wait, results, []);
}
```

This:

- imports the Python function
- creates a `map` function and helpers
- runs `complicated_stuff` on every element of an array, **at the same time**
  (with `async`)
- waits for all results to come back

There are several new concepts here, particularly in the implementation of
`map`. Briefly, `map` works by calling itself recursively (which the compiler
optimises) until the list of inputs runs out, at which point it returns the
accumulated results. This will eventually be in the Hark "standard library" -
coming soon!


### Test first!

```shell
$ hark service.hk
Complicated! 1
Complicated! 2
Complicated! 3
Complicated! 4
Complicated! 5
[10, 20, 30, 40, 50]

-- 0s
```

Looks right enough.

### Deploy

Ensure your AWS credentials are correctly configured, and that
`AWS_DEFAULT_REGION` is set.

```shell
$ hark deploy
```

Reply *Create a new self-hosted instance (using local AWS credentials)* to the
question -- this will create a new Hark instance in your account.

Expected output:

```
Target: Self-hosted instance xxx.......

✔ Deploying infrastructure Build data: ....../.hark/
✔ Checking API Hark 0....
✔ Deploying service.hk

Done. `hark invoke` to run main().

-- 56s
```

You could also deploy with the verbose flag, `-v`, to see details of what is
changed.

### Run!

This will take a little while, because the Lambda function is being spun up for
the first time.

```shell
$ hark invoke
Target: Self-hosted instance xxx.......

✔ main(...) 3e50fbf3-5e3e-47bf-b949-a93b1cdf08b0
✔ Getting stdout...

Thread   Time
=========================================
     1   +0:00:00          Complicated! 1
     2   +0:00:01.280391   Complicated! 2
     4   +0:00:02.358765   Complicated! 4
     3   +0:00:02.652161   Complicated! 3
     5   +0:00:03.700506   Complicated! 5


=>
[10, 20, 30, 40, 50]

-- 17s
```

Success! Lambda was invoked 6 times here -- once for each thread (including the
top-level thread 0).
