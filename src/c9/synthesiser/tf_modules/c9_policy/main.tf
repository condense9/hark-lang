
data "aws_region" "current" {}


data "aws_iam_policy_document" "c9" {
  statement {
    actions   = ["s3:*"]
    resources = ["arn:aws:s3:::"]
  }
  statement {
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
    ]
    resources = ["arn:aws:dynamodb:${data.aws_region.current.name}:*:*"]
  }
}

resource "aws_iam_policy" "c9" {
  name        = "c9main"
  description = "C9 Main Lambda Policy"

  policy = data.aws_iam_policy_document.c9.json
}


output "arn" {
  value = aws_iam_policy.c9.arn
}
