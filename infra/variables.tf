variable "aws_region" {
  description = "Região da AWS onde os recursos serão criados"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome base do projeto"
  type        = string
  default     = "mock-interview"
}

variable "environment" {
  description = "Ambiente de deploy"
  type        = string
  default     = "dev"
}