# infra/website.tf

# 1. O Bucket S3 para o Frontend
resource "aws_s3_bucket" "frontend_bucket" {
  bucket        = "${var.project_name}-frontend-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = true # Permite deletar o bucket mesmo cheio (útil para dev)
}

# 2. Configura o bucket para agir como um Site Estático
resource "aws_s3_bucket_website_configuration" "frontend_website" {
  bucket = aws_s3_bucket.frontend_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html" # Redireciona 404 para index (padrão SPA/React)
  }
}

# 3. Desbloqueia o acesso público (Passo 1 de 2)
resource "aws_s3_bucket_public_access_block" "frontend_public_access" {
  bucket = aws_s3_bucket.frontend_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# 4. Política de Leitura Pública (Passo 2 de 2)
# Permite que qualquer pessoa na internet veja seu site
resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend_bucket.arn}/*"
      }
    ]
  })

  # Espera o bloqueio público ser removido antes de aplicar a política
  depends_on = [aws_s3_bucket_public_access_block.frontend_public_access]
}
# --- 5. CloudFront (CDN + HTTPS) ---
resource "aws_cloudfront_distribution" "s3_distribution" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  # A origem é o endereço do site do S3
  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend_website.website_endpoint
    origin_id   = "S3-${aws_s3_bucket.frontend_bucket.id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # CloudFront fala com S3 via HTTP
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Configuração de Cache e HTTPS forçado
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https" # O PULO DO GATO: Força HTTPS
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # Certificado SSL Gratuito da AWS
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  # Restrições Geográficas (Liberado pro mundo todo)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
