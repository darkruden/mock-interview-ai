# --- 1. Random ID (Garante nome único global para o Bucket) ---
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# --- 2. S3 Bucket (Armazenamento de Mídia) ---
resource "aws_s3_bucket" "media_bucket" {
  bucket        = "${var.project_name}-media-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = true # Permite deletar o bucket mesmo com arquivos (útil para dev)
}

# Segurança: Bloqueio de Acesso Público Total
resource "aws_s3_bucket_public_access_block" "media_bucket_access" {
  bucket = aws_s3_bucket.media_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Configuração CORS (Cross-Origin Resource Sharing)
# Permite que o Frontend faça upload direto (Direct-to-Cloud pattern)
resource "aws_s3_bucket_cors_configuration" "media_bucket_cors" {
  bucket = aws_s3_bucket.media_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = ["*"] # Em produção, alterar para o domínio do frontend
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# --- 3. DynamoDB Table (Banco de Dados Serverless) ---
resource "aws_dynamodb_table" "sessions_table" {
  name         = "${var.project_name}-sessions-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # Modelo On-Demand (Zero custo fixo)
  hash_key     = "session_id"      # Chave Primária

  attribute {
    name = "session_id"
    type = "S" # String (UUID)
  }

  # TTL: Limpeza automática de sessões antigas
  ttl {
    attribute_name = "expire_at"
    enabled        = true
  }
}