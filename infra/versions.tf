terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # --- CONFIGURAÇÃO DO REMOTE BACKEND ---
  backend "s3" {
    bucket         = "mock-interview-terraform-state-backend"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-lock-table"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "MockInterviewAI"
      ManagedBy = "Terraform"
    }
  }
}
