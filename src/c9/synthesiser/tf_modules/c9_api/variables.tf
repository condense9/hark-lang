# https://github.com/vcz-fr/tf-crud-demo/blob/master/infrastructure/modules/global/aws_api-gateway/vars.tf
variable "name" {
  type        = string
  description = "API Gateway name"
}

variable "hash" {
  type        = string
  description = "Hash of API content - changes to this will redeploy the API"
}
