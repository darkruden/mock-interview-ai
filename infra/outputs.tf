output "s3_bucket_name" {
  description = "Nome gerado do Bucket S3"
  value       = aws_s3_bucket.media_bucket.id
}

output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB"
  value       = aws_dynamodb_table.sessions_table.name
}

output "aws_region" {
  value = var.aws_region
}

output "lambda_function_name" {
  description = "Nome da função Lambda criada"
  value       = aws_lambda_function.get_upload_url.function_name
}

output "api_endpoint" {
  description = "URL base da API pública"
  value       = aws_apigatewayv2_api.main_api.api_endpoint
}