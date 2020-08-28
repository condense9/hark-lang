# Hello Worlds!

Hello world in hark looks like this. Type or paste this in your favourite editor.

```javascript
// service.hk

fn hello_world() {
  "Hello from hark!"
}
```

Which we can run locally:

```bash
hark service.hk -f hello_world
```

## Explanation

Hark files contain imports and Hark functions. The command line program allows
us to specify which Hark function to invoke with the `-f` argument. The age old
`main` function convention also applies in Hark.

Our `service.hk` when run without an explicit function will tell us that we dont have a `main` function.

```bash
hark service.hk
```
```
Can't run function `main'.
Does it exist in service.hk?
```

We can solve that easily by adding a main.

```javascript
// service.hk

fn hello_world() {
  "Hello from hark!"
}

fn main() {
  hello_world()
}
```
