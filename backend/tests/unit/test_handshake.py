import json
import pytest
from handlers.get_upload_url import lambda_handler

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
    assert "https://" in body["upload_url"] # Verifica se gerou uma URL

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