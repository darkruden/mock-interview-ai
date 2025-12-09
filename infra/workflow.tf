# --- 1. IAM Role para a Step Function ---
# Permite que a Step Function invoque Lambdas
resource "aws_iam_role" "step_function_role" {
  name = "${var.project_name}-step-function-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "step_function_policy" {
  name = "${var.project_name}-step-function-policy"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.process_audio.arn
      }
    ]
  })
}

# --- 2. A Máquina de Estados (State Machine) ---
resource "aws_sfn_state_machine" "analysis_workflow" {
  name     = "${var.project_name}-workflow-${var.environment}"
  role_arn = aws_iam_role.step_function_role.arn

  # Definição do Fluxo em JSON (Amazon States Language)
  definition = jsonencode({
    Comment = "Orquestração de Análise de Entrevistas"
    StartAt = "AnalyzeAudio"
    States = {
      AnalyzeAudio = {
        Type     = "Task"
        Resource = aws_lambda_function.process_audio.arn
        End      = true

        # Retentativa Automática (Robustez Enterprise)
        Retry = [
          {
            ErrorEquals     = ["States.ALL"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]
      }
    }
  })
}
