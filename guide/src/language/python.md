# Python inter-op

**NOTE**: this syntax is unstable and very likely to change before Hark v1.0, in
particular, to permit qualified imports.

Python functions (or callables) are imported into a Hark program with `import`,
with the following signature:

```javascript
import(name, module, num_args);
```

* `name`: identifier, the name of the function to import
* `module`: identifier, module to import from
* `num_args`: int, number of arguments the function takes


For example:

```javascript
import(foo, my_package.bar, 1);
```

