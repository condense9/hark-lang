# Manual implementation

Using Serverless Components, which seems to be the simplest method (on
03/21/20).

Run `serverless`. The output should be something like:

```
  helloWorld:
    name:        l68i5zw-dpud7rx
    description: AWS Lambda Component
    memory:      128
    timeout:     10
    code:        ./src
    bucket:      undefined
    shims:       (empty array)
    handler:     index.hello
    runtime:     python3.8
    env:
    role:
      arn: arn:aws:iam::297409317403:role/l68i5zw-wzomplu
    arn:         arn:aws:lambda:eu-west-2:297409317403:function:l68i5zw-dpud7rx
    region:      eu-west-2

  restApi:
    name:      l68i5zw-42jqy8
    id:        sy4vihqesf
    endpoints:
      -
        path:         /hello
        method:       GET
        function:     arn:aws:lambda:eu-west-2:297409317403:function:l68i5zw-dpud7rx
        authorizer:   null
        url:          https://sy4vihqesf.execute-api.eu-west-2.amazonaws.com/dev/hello
        authorizerId: undefined
        id:           snzasc
    url:       https://sy4vihqesf.execute-api.eu-west-2.amazonaws.com/dev
```

Then browse to `url` to confirm it works.
