import json
import pytest
from unittest.mock import MagicMock
from handlers.get_upload_url import lambda_handler

# --- Testes de Sucesso ---

def test_handshake_creates_session_successfully(s3_client, dynamodb_resource):
    """
    Valida se a função cria um registro no DynamoDB e retorna a URL assinada.
    """
    # 1. Arrange (Recursos mockados via conftest.py)
    mock_clients = (s3_client, dynamodb_resource)
    
    payload = {
        "candidate_name": "QA Tester",
        "question_id": "Q1",
        "job_description": "Vaga de Python Pleno"
    }
    event = {"body": json.dumps(payload)}

    # 2. Act
    response = lambda_handler(event, {}, clients=mock_clients)
    body = json.loads(response["body"])

    # 3. Assert - Resposta da API
    assert response["statusCode"] == 201
    assert "upload_url" in body
    assert "session_id" in body
    # O moto gera URLs locais, então verificamos se é string
    assert isinstance(body["upload_url"], str) 

    # 4. Assert - Persistência no Banco
    table = dynamodb_resource.Table("MockInterviewSessions-Test")
    item = table.get_item(Key={'session_id': body['session_id']})['Item']
    
    assert item['status'] == 'PENDING_UPLOAD'
    assert item['candidate_name'] == "QA Tester"
    assert item['job_description'] == "Vaga de Python Pleno"

def test_handshake_truncates_huge_description(s3_client, dynamodb_resource):
    """
    Segurança: Verifica se descrições gigantes são cortadas para economizar banco.
    """
    mock_clients = (s3_client, dynamodb_resource)
    huge_desc = "A" * 6000 # 6000 caracteres
    
    event = {"body": json.dumps({"job_description": huge_desc})}
    
    response = lambda_handler(event, {}, clients=mock_clients)
    body = json.loads(response["body"])
    
    table = dynamodb_resource.Table("MockInterviewSessions-Test")
    item = table.get_item(Key={'session_id': body['session_id']})['Item']
    
    # Deve ter cortado para 5000
    assert len(item['job_description']) == 5000

# --- Testes de Erro (Novos) ---

def test_handshake_internal_server_error(s3_client, dynamodb_resource):
    """Cenário: Falha crítica em algum serviço AWS (cai no bloco except)."""
    # Arrange
    # Mockamos um cliente S3 que falha ao gerar URL
    mock_s3_broken = MagicMock()
    mock_s3_broken.generate_presigned_url.side_effect = Exception("Erro Fatal S3")
    
    mock_clients = (mock_s3_broken, dynamodb_resource)
    event = {"body": "{}"} # Body vazio válido JSON

    # Act
    response = lambda_handler(event, {}, clients=mock_clients)
    
    # Assert
    assert response["statusCode"] == 500
    # Verifica se o erro capturado é o que lançamos
    assert "Erro Fatal S3" in response["body"]