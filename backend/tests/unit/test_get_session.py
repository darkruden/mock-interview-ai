import json
import pytest
from handlers.get_session import lambda_handler

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