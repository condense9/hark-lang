output "deployment" {
  value = aws_api_gateway_deployment.api-deployment
}

output "root_resource_id" {
  value = aws_api_gateway_resource.root.id
}

output "execution_arn" {
  value = aws_api_gateway_rest_api.api.execution_arn
}
