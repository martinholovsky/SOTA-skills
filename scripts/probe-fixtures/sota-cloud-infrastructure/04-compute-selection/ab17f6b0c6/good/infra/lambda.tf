resource "aws_lambda_function" "payments" {
  function_name = "payments"
  role          = aws_iam_role.payments.arn
  handler       = "main.handler"
  runtime       = "python3.12"
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.payments.id]
  }
}
