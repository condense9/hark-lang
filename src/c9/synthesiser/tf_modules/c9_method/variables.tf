# https://github.com/TailorDev/hello-lambda/blob/master/api_method/main.tf

variable "rest_api_id" {
  description = "The ID of the associated REST API"
}

variable "resource_id" {
  description = "The API resource ID"
}

variable "method" {
  description = "The HTTP method"
}

variable "path" {
  description = "The API resource path"
}

variable "handler" {
  description = "The lambda name to invoke"
}
