# https://github.com/vcz-fr/tf-crud-demo/blob/master/infrastructure/modules/global/aws_api-gateway/resource.tf
# And, https://github.com/TailorDev/hello-lambda/blob/master/hello_lambda.tf

resource "aws_api_gateway_rest_api" "api" {
  name = var.name
}


# https://www.terraform.io/docs/providers/aws/d/api_gateway_resource.html
resource "aws_api_gateway_resource" "root" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = ""
}


resource "aws_api_gateway_deployment" "api-deployment" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "latest"

  # Detects changes in the hash and consequently deploys the new API to the
  # stage
  description = "C9 API [${var.hash}]"
}
