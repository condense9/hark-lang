# Example

Showcase a few things Teal can do. [`./hello.tl`](hello.tl) contains function
definitions, and imports Python code from `./src`.

Requirements:
- [jq](https://stedolan.github.io/jq/)
- [Serverless Framework](https://serverless.com/)

Functions can be run locally:

```
$ teal hello.tl
```

And to call a function (note the double-quotes around the argument):

```
$ teal hello.tl -f printer '"Hello world!"'
```


## ASTs and decompilation

Sometimes it can be helpful to visualise your program:

```
$ teal ast hello.tl -f main -o ast.png
$ open ast.png
```

Or to list the bytecode:

```
$ teal asm hello.tl
```


## Run with Multiple Processes

The normal `teal hello.tl` command stores program state in memory, and uses Python
threads for concurrency. Pass the `--storage` and `--concurrency` parameters to
change this.

Currently the only storage backend that supports concurrency is DynamoDB. Proper
concurrency is achieved using multiple Python processes (instead of threads).

Start a local dynamodb server in another terminal first:

```
$ ../../scripts/dynamodb_local.sh
```

Then:

```
$ export TL_REGION=eu-west-2
$ export DYNAMODB_ENDPOINT=http://localhost:9000 
$ export DYNAMODB_TABLE=TlSessions
$ teal hello.tl --storage dynamodb --concurrency processes
```

And for a good example of concurrency,

```
$ teal hello.tl --storage dynamodb --concurrency processes --fn concurrent 5
```


## Deployment to AWS

Finally, AWS Lambda can be used as the concurrency backend, alongside DynamoDB
for storage.

The infrastructure can be deployed any way you like, and there are bash scripts
in `../../scripts` to aid with packaging. This example uses the Serverless
Framework to deploy it.

First, create the AWS Lambda distribution package and the source code layer:

```
$ ../../scripts/make_lambda_dist.sh
$ ../../scripts/make_layer.sh
```

This will create `dist.zip` and `layersrc.zip` in the current directory, which
contains the "interpreter" code and the Python code imported from `hello.tl`.

Deploy the infrastructure:

```
$ sls deploy
```

This will create three Lambda functions, and a DynamoDB database. The functions are:
- `set_exe` - set the executable program (i.e. the definitions of functions)
- `new` - call a function with some arguments (start a new evaluation session)
- `resume` - resume an evaluation session (used internally)

Upload the program by POSTing to `/set_exe`:

```
$ ../../scripts/upload.sh hello.tl
```

Now definitions in `hello.tl` are callable, by POSTing to `new`.

Note that the source code layer can be updated independently - you only have to
deploy the Teal infrastructure (`dist.zip`) once.


### Invoke

Call the `new` Lambda function, and pass the configuration as in the payload.

```
$ sls invoke -f new -p test_printer.json | jq -r | jq .
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
immediately, or waits until the execution of the Teal function finishes.

