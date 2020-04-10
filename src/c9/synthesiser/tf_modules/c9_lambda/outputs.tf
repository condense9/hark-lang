output "arn" {
  value = aws_lambda_function.lambda.arn
}

output "role_arn" {
  value = aws_iam_role.lambda.arn
}

output "role_name" {
  value = aws_iam_role.lambda.name
}

output "invoke_arn" {
  value = aws_lambda_function.lambda.invoke_arn
}
