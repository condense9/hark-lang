# https://github.com/TailorDev/hello-lambda/blob/master/api_method/main.tf

# The HTTP method in the API for the path part
resource "aws_api_gateway_method" "request_method" {
  rest_api_id   = var.rest_api_id
  resource_id   = var.resource_id
  http_method   = var.method
  authorization = "NONE"
}

# Integration - connect method to lambda
resource "aws_api_gateway_integration" "request_method_integration" {
  rest_api_id = var.rest_api_id
  resource_id = var.resource_id
  http_method = aws_api_gateway_method.request_method.http_method
  type        = "AWS_PROXY"
  uri         = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.handler}/invocations"

  # AWS lambdas can only be invoked with the POST method
  integration_http_method = "POST"
}

resource "aws_lambda_permission" "allow_api_gateway" {
  function_name = var.handler
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.rest_api_id}/*/${var.method}/${var.path}"
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}


# No need to set up method responses
# https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-response.html
