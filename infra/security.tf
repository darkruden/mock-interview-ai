# --- 1. O Banco de Usuários (User Pool) ---
resource "aws_cognito_user_pool" "users" {
  name = "${var.project_name}-users-${var.environment}"

  # Permite login usando o e-mail
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  # Configuração de e-mail (usamos o padrão do Cognito para ser grátis/rápido)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }
}

# --- 2. O Cliente da Aplicação (App Client) ---
# É a "porta" por onde o React vai bater para pedir login
resource "aws_cognito_user_pool_client" "client" {
  name = "${var.project_name}-react-client-${var.environment}"

  user_pool_id = aws_cognito_user_pool.users.id

  # CRÍTICO: Para SPAs (React), NÃO geramos segredo (client secret)
  # pois o navegador não consegue guardá-lo com segurança.
  generate_secret = false

  # Fluxos de autenticação permitidos
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}
