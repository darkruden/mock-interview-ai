# --- 1. O API Gateway (Tipo HTTP - Mais barato e rápido que REST) ---
resource "aws_apigatewayv2_api" "main_api" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  # Configuração de CORS (Vital para o Frontend funcionar)
  cors_configuration {
    allow_origins = ["*"] # Em produção, coloque o domínio do seu site
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}

# --- 2. Stage (Ambiente de Deploy: $default é o automático) ---
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.main_api.id
  name        = "$default"
  auto_deploy = true
}

# --- 3. Integração: Conectar API -> Lambdas ---

# Integração para POST /sessions (Handshake)
resource "aws_apigatewayv2_integration" "upload_integration" {
  api_id                 = aws_apigatewayv2_api.main_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_upload_url.invoke_arn
  payload_format_version = "2.0"
}

# Integração para GET /sessions/{id} (Consulta)
resource "aws_apigatewayv2_integration" "session_integration" {
  api_id                 = aws_apigatewayv2_api.main_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_session.invoke_arn
  payload_format_version = "2.0"
}

# --- 4. Rotas (Endereços da API) ---

resource "aws_apigatewayv2_route" "post_sessions" {
  api_id    = aws_apigatewayv2_api.main_api.id
  route_key = "POST /sessions"
  target    = "integrations/${aws_apigatewayv2_integration.upload_integration.id}"
}

resource "aws_apigatewayv2_route" "get_session_by_id" {
  api_id    = aws_apigatewayv2_api.main_api.id
  route_key = "GET /sessions/{session_id}"
  target    = "integrations/${aws_apigatewayv2_integration.session_integration.id}"
}

# --- 5. Permissões (Dar chave da API para a Lambda) ---
# A Lambda precisa saber que o API Gateway tem permissão de invocá-la

resource "aws_lambda_permission" "api_gw_upload" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_upload_url.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gw_session" {
  statement_id  = "AllowExecutionFromAPIGatewayGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_session.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main_api.execution_arn}/*/*"
}