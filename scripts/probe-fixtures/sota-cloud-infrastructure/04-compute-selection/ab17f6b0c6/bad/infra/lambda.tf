resource "aws_lambda_function" "payments" {
  function_name = "payments"
  role          = aws_iam_role.payments.arn
  handler       = "main.handler"
  runtime       = "python3.12"
}
