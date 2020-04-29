# Example

Showcase a few things C9 can do.

Requirements:
- [jq](https://stedolan.github.io/jq/)
- [Serverless Framework](https://serverless.com/)

`hello.c9` contains function definitions, and imports Python code from `src`.

Functions can be run locally:

```
$ c9 hello.c9
```

And to call a function (note the double-quotes around the argument):

```
$ c9 hello.c9 -f printer '"Hello world!"'
```


## Deployment to AWS

This example uses the Serverless Framework to deploy the infrastructure.

First, create the AWS Lambda distribution package and the source code layer:

```
$ ../scripts/make_lambda_dist.sh
$ ../scripts/make_layer.sh
```

This will create `dist.zip` and `layersrc.zip` in the current directory, which
contains the "interpreter" code and the Python code imported from `hello.c9`.

Deploy the infrastructure:

```
$ sls deploy
```

Finally, upload the program:

```
$ ../scripts/upload.sh hello.c9
```

Now definitions in `hello.c9` are callable.


## Calling deployed functions

Invoke a function called `new`, and pass a JSON file containing the arguments.

```
$ sls invoke -f new -p test_main.json | jq -r | jq .
```

Example (pseudo) JSON file:

```json
{
  "function": "printer",   // the function to call
  "args": ["\"HI!\""],     // arguments to pass to the function

  // optional:
  "wait_for_finish": true, // wait for execution to finish
  "timeout": 10,           // timeout when waiting
  "check_period": 1        // period of the finish checks
}
```

The last three options configure whether the *Lambda function* returns
immediately, or waits until the execution of the C9 function finishes.

