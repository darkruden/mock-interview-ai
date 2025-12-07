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

output "frontend_bucket_name" {
  description = "Nome do bucket do frontend (para deploy)"
  value       = aws_s3_bucket.frontend_bucket.id
}

output "website_url" {
  description = "URL pública do Frontend"
  value       = aws_s3_bucket_website_configuration.frontend_website.website_endpoint
}

output "cloudfront_url" {
  description = "URL Segura (HTTPS) do site"
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
}
