# --- 1. Preparação do Código (Zip) ---
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../src"          # Pega todo o código da pasta src
  output_path = "lambda_function.zip"
}

# --- 2. IAM Role (Crachá de Segurança da Lambda) ---
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Permissões Básicas (Logs + Acesso ao S3 e DynamoDB)
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Permissão para criar Logs (CloudWatch)
      {
        Effect = "Allow"
        Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      # Permissão para Escrever/Ler no DynamoDB
      {
        Effect = "Allow"
        Action = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem"]
        Resource = aws_dynamodb_table.sessions_table.arn
      },
      # Permissão para Gerar URL de Upload no S3
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.media_bucket.arn}/*"
      }
    ]
  })
}

# --- 3. A Função Lambda (Get Upload URL) ---
resource "aws_lambda_function" "get_upload_url" {
  function_name = "${var.project_name}-get-upload-url-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  
  # Define o arquivo zipado e o hash (para saber quando atualizar)
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  runtime = "python3.11"
  handler = "handlers.get_upload_url.lambda_handler" # Caminho: pasta.arquivo.funcao
  timeout = 10 # Segundos

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.media_bucket.id
      TABLE_NAME  = aws_dynamodb_table.sessions_table.name
    }
  }
}