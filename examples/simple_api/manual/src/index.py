"""A manual version of the same"""

import json

# https://medium.com/@dwdraju/python-function-on-aws-lambda-with-api-gateway-endpoint-288eae7617cb
#
# Input: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format
# Output: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-output-format

def hello(event, context):
    print(str(event))
    return dict(
        statusCode=200,
        # isBase64Encoded="false",
        # headers=dict(...),
        body=json.dumps(dict(message="Hello World!"))
    )
