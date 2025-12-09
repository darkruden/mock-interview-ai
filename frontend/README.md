# 🤖 Mock Interview AI (Serverless Edition)

![Build Status](https://github.com/darkruden/mock-interview-ai/actions/workflows/deploy.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-cyan)
![Terraform](https://img.shields.io/badge/Infra-Terraform-purple)
![AWS](https://img.shields.io/badge/Cloud-AWS-orange)

Uma plataforma SaaS Serverless para simulação de entrevistas técnicas. O usuário grava uma resposta em áudio, cola a descrição da vaga (Job Description) e recebe feedback instantâneo gerado por IA Multimodal (Google Gemini), avaliando tanto a técnica quanto a comunicação.

---

## 🏗️ Arquitetura Atual (Event-Driven)

O sistema utiliza uma arquitetura **Direct-to-Cloud** para uploads de alta performance e processamento assíncrono.

````mermaid
graph TD
    User[Usuário / React Frontend]

    subgraph "Camada de API (Síncrona)"
        APIGW[API Gateway HTTP]
        AuthLambda[Lambda: Get Upload URL]
        DB[(DynamoDB)]
    end

    subgraph "Camada de Storage (Assíncrona)"
        S3[S3 Bucket: Mídia]
        Gemini[Google Gemini 1.5 Flash]
        ProcLambda[Lambda: Processor]
    end

    %% Fluxos
    User -->|1. POST /sessions + Job Desc| APIGW
    APIGW --> AuthLambda
    AuthLambda -->|Salva Metadados| DB
    AuthLambda -->|Retorna URL Assinada| User

    User -->|2. Upload Direto (PUT)| S3
    S3 -->|3. Trigger Event| ProcLambda

    ProcLambda -->|4. Lê Contexto| DB
    ProcLambda -->|5. Envia Áudio + Prompt| Gemini
    ProcLambda -->|6. Salva Feedback| DB

    User -.->|7. Polling de Resultado| APIGW
🚀 Features Entregues[x] Arquitetura 100% Serverless (Custo zero quando ocioso).[x] Upload Direto (Presigned URLs): O áudio não passa pela API, vai direto do browser para o S3.[x] Inteligência Contextual: A IA avalia o candidato com base na Descrição da Vaga fornecida.[x] CI/CD Enterprise: Pipeline GitHub Actions configurada com Terraform Remote State.[x] Anti-Alucinação: Prompts defensivos para evitar feedbacks falsos em áudios mudos.[x] Frontend Moderno: React + TailwindCSS + Framer Motion (Cyberpunk Theme).🛠️ Stack TecnológicaComponenteTecnologiaJustificativaBackendPython 3.11 (AWS Lambda)Nativo para IA, Boto3 robusto.FrontendReact (Vite)SPA rápida e reativa.Infra (IaC)TerraformGerenciamento de estado e reprodução de ambiente.BancoDynamoDBNoSQL escalável com TTL automático.IAGoogle Gemini 1.5 FlashMultimodalidade nativa (lê áudio mp3 direto).DevOpsGitHub ActionsDeploy automático de Infra, Backend e Frontend.🔌 API Reference1. Iniciar Sessão (Handshake)POST /sessionsJSON{
  "candidate_name": "João Silva",
  "job_description": "Requisitos: Experiência com AWS Lambda e Terraform."
}
Response (201):JSON{
  "session_id": "550e8400-e29b...",
  "upload_url": "[https://s3.amazonaws.com/](https://s3.amazonaws.com/)..."
}
2. Consultar ResultadoGET /sessions/{session_id}Response (200):JSON{
  "status": "COMPLETED",
  "ai_feedback": {
    "technical_score": 85,
    "clarity_score": 90,
    "feedback": "O candidato demonstrou domínio sobre..."
  }
}
📦 Como Rodar LocalmentePré-requisitosNode.js 18+Python 3.11TerraformConta AWS ConfiguradaBackend (Testes)Bash# Rodar teste E2E (Simula fluxo completo na nuvem)
python backend/tests/integration/test_upload_flow.py
FrontendBashcd frontend
npm install
npm run dev
Projeto desenvolvido como parte de um roadmap de Arquitetura de Software Avançada.
---

### O que fazer com o arquivo `.docx`?
O arquivo `planejamento geral.docx` é o seu "Documento de Design" (Design Doc). Ele é menos dinâmico que o README.
* **Recomendação:** Não precisamos editá-lo agora. Vamos finalizá-lo apenas no final do projeto (Módulo C completo), para que ele sirva como o "Relatório Final de Entrega".

### Próximo Passo
Atualize o `README.md` na sua máquina, faça o commit e push para a `develop` (ou direto na `main` se preferir, já que é documentação).

```bash
git add README.md
git commit -m "docs: atualiza readme com arquitetura do modulo B"
git push origin develop

````
