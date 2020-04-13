# Synthesis and Deployment

The C9 synthesiser takes a Service and generates a directory containing

- infrastructure-as-code
- at least one shell script to kick-off deployment (`deploy.sh`) 

The intention is that this directory is never modified by hand, and is treated
as a reproducible "blob".

The workflow is:

```shell
$ c9 compile -o build (...arguments...)
...
$ chmod +x build/deploy.sh
$ ./build/deploy.sh
```

The synthesiser is highly flexible, and can be easily customised.

How? Coming soon...
