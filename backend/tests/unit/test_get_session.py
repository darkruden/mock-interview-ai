import json
import pytest
from unittest.mock import MagicMock
from handlers.get_session import lambda_handler

# --- Testes de Sucesso ---

def test_get_session_found(dynamodb_resource):
    """Verifica se retorna os dados corretamente quando o ID existe."""
    # 1. Arrange
    table = dynamodb_resource.Table("MockInterviewSessions-Test")
    table.put_item(Item={
        "session_id": "session-123",
        "status": "COMPLETED",
        "ai_feedback": {"score": 95}
    })
    
    event = {"pathParameters": {"session_id": "session-123"}}

    # 2. Act
    response = lambda_handler(event, {}, dynamodb_resource=dynamodb_resource)
    body = json.loads(response["body"])

    # 3. Assert
    assert response["statusCode"] == 200
    assert body["session_id"] == "session-123"
    assert body["status"] == "COMPLETED"
    assert body["ai_feedback"]["score"] == 95

def test_get_session_not_found(dynamodb_resource):
    """Verifica se retorna 404 quando o ID não existe."""
    event = {"pathParameters": {"session_id": "non-existent-id"}}
    
    response = lambda_handler(event, {}, dynamodb_resource=dynamodb_resource)
    
    assert response["statusCode"] == 404
    assert "not found" in response["body"]

# --- Testes de Erro (Novos) ---

def test_get_session_missing_id_parameter(dynamodb_resource):
    """Cenário: O evento não tem pathParameters ou session_id (Erro 400)."""
    # Act
    # Passamos um evento vazio ou sem a chave esperada
    response = lambda_handler({}, {}, dynamodb_resource=dynamodb_resource)
    
    # Assert
    assert response["statusCode"] == 400
    assert "Missing session_id" in response["body"]

def test_get_session_dynamodb_failure(dynamodb_resource):
    """Cenário: O DynamoDB lança uma exceção inesperada (Erro 500)."""
    # Arrange
    # Criamos um mock que QUEBRA quando chamado
    mock_db_broken = MagicMock()
    mock_table = MagicMock()
    # Configura o get_item para lançar uma exceção genérica
    mock_table.get_item.side_effect = Exception("DynamoDB Explodiu")
    mock_db_broken.Table.return_value = mock_table
    
    event = {"pathParameters": {"session_id": "123"}}

    # Act
    response = lambda_handler(event, {}, dynamodb_resource=mock_db_broken)
    
    # Assert
    assert response["statusCode"] == 500
    assert "Internal Server Error" in response["body"]