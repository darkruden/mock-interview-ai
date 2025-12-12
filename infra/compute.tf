# --- 1. Preparação do Código (Zip) ---
data "archive_file" "lambda_zip" {
  type = "zip"
  # MUDANÇA AQUI: Aponta para a pasta de build, não para o src original
  source_dir  = "../build_package"
  output_path = "lambda_function.zip"
}

# --- 2. IAM Role (Crachá de Segurança da Lambda) ---
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
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
      # Logs
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      # DynamoDB (Leitura e Escrita)
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"]
        Resource = aws_dynamodb_table.sessions_table.arn
      },
      # S3 (CRÍTICO: Permissão para baixar o áudio)
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]      # PutObject opcional se quiser salvar logs
        Resource = "${aws_s3_bucket.media_bucket.arn}/*" # O "/*" é vital para acessar os objetos
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
  timeout = 10                                       # Segundos

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.media_bucket.id
      TABLE_NAME  = aws_dynamodb_table.sessions_table.name
    }
  }
}

# --- 4. A Função Lambda Processor (O Cérebro) ---
resource "aws_lambda_function" "process_audio" {
  function_name = "${var.project_name}-process-audio-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  # Aponta para o mesmo ZIP gerado pelo build
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11" # Obrigatório para a nova SDK google-genai

  # IMPORTANTE: O handler deve bater com: pasta.arquivo.funcao
  # Como seu zip tem a pasta 'handlers', e o arquivo é 'process_audio.py', e a função é 'handler'
  handler = "handlers.process_audio.handler"

  # Performance Tuning
  timeout     = 60  # Aumentado para 60s (IA demora)
  memory_size = 512 # Aumentado para processar JSON/Áudio mais rápido

  environment {
    variables = {
      # Conecta com a variável que definimos no Python
      AUDIO_BUCKET_NAME = aws_s3_bucket.media_bucket.id
      SESSIONS_TABLE    = aws_dynamodb_table.sessions_table.name
      GEMINI_API_KEY    = var.gemini_api_key
    }
  }
}

# --- 5. O Gatilho (S3 Trigger) ---
# Dá permissão para o S3 invocar esta Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_execution.function_name # <--- MUDOU AQUI
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.media_bucket.arn
}

# Configura o S3 para avisar a Lambda quando chegar arquivo novo
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.media_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.start_execution.arn # <--- MUDOU AQUI
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".mp3"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# --- 6. Lambda de Leitura (Get Session) ---
resource "aws_lambda_function" "get_session" {
  function_name = "${var.project_name}-get-session-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11"
  handler = "handlers.get_session.lambda_handler"
  timeout = 5

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.sessions_table.name
    }
  }
}

# [NOVO] Lambda Gatilho (Recebe S3 -> Inicia Workflow)
resource "aws_lambda_function" "start_execution" {
  function_name = "${var.project_name}-start-execution-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11"
  handler = "handlers.start_execution.lambda_handler"
  timeout = 10

  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.analysis_workflow.arn
    }
  }
}

# Lambda para gerar Tokens Efêmeros do Gemini
resource "aws_lambda_function" "get_gemini_token" {
  function_name = "${var.project_name}-get-token-${var.environment}"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.11"
  handler = "handlers.get_gemini_token.lambda_handler"
  timeout = 10

  environment {
    variables = {
      GEMINI_API_KEY = var.gemini_api_key
    }
  }
}
