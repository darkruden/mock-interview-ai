# --- 1. O API Gateway (Tipo HTTP - Mais barato e rápido que REST) ---
resource "aws_apigatewayv2_api" "main_api" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  # Configuração de CORS (Vital para o Frontend funcionar)
  cors_configuration {
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins = ["*"] # Em produção real, você trocaria "*" pela URL do CloudFront
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
  api_id             = aws_apigatewayv2_api.main_api.id
  route_key          = "POST /sessions"
  target             = "integrations/${aws_apigatewayv2_integration.upload_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_auth.id
}

resource "aws_apigatewayv2_route" "get_session_by_id" {
  api_id             = aws_apigatewayv2_api.main_api.id
  route_key          = "GET /sessions/{session_id}"
  target             = "integrations/${aws_apigatewayv2_integration.session_integration.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_auth.id
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

# --- 6. O Porteiro (Cognito Authorizer) ---
resource "aws_apigatewayv2_authorizer" "cognito_auth" {
  api_id           = aws_apigatewayv2_api.main_api.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.client.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
  }
}

# Integração da Lambda de Token
resource "aws_apigatewayv2_integration" "token_integration" {
  api_id                 = aws_apigatewayv2_api.main_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_gemini_token.invoke_arn
  payload_format_version = "2.0"
}

# Rota GET /auth/gemini-token (Protegida pelo Cognito)
resource "aws_apigatewayv2_route" "get_token" {
  api_id    = aws_apigatewayv2_api.main_api.id
  route_key = "GET /auth/gemini-token"
  target    = "integrations/${aws_apigatewayv2_integration.token_integration.id}"

  # Segurança Máxima: Só usuários logados pegam token da IA
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_auth.id
}

# Permissão para o API Gateway invocar a Lambda
resource "aws_lambda_permission" "api_gw_token" {
  statement_id  = "AllowExecutionFromAPIGatewayToken"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_gemini_token.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main_api.execution_arn}/*/*/auth/gemini-token"
}


# Integração da Lambda process_audio
resource "aws_apigatewayv2_integration" "process_audio_integration" {
  api_id                 = aws_apigatewayv2_api.main_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.process_audio.invoke_arn
  payload_format_version = "2.0"
}

# Rota POST /sessions/process
resource "aws_apigatewayv2_route" "post_process_audio" {
  api_id    = aws_apigatewayv2_api.main_api.id
  route_key = "POST /sessions/process"
  target    = "integrations/${aws_apigatewayv2_integration.process_audio_integration.id}"

  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_auth.id
}

# Permissão para o API Gateway invocar a Lambda
resource "aws_lambda_permission" "api_gw_process_audio" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_audio.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main_api.execution_arn}/*/*"
}
