import pytest
import json
from unittest.mock import MagicMock
from handlers.process_audio import lambda_handler

# Dados de teste
SESSION_ID = "test-session-123"
BUCKET_NAME = "mock-interview-tests-bucket"
S3_KEY = f"uploads/{SESSION_ID}/audio.mp3"
TABLE_NAME = "MockInterviewSessions-Test"

@pytest.fixture
def mock_genai_client():
    """
    Mock atualizado para a nova biblioteca google-genai (v1.0+).
    Simula: client.files.upload, client.files.get, client.models.generate_content
    """
    # 1. Mock do objeto File
    mock_file = MagicMock()
    mock_file.state.name = "ACTIVE"
    mock_file.name = "files/123"

    # 2. Mock da resposta da IA
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "technical_score": 85,
        "summary": "Teste ok",
        "feedback": "Feedback ok"
    })

    # 3. Monta o Client Mock
    client_mock = MagicMock()
    
    # Configura os sub-serviços (files e models)
    client_mock.files.upload.return_value = mock_file
    client_mock.files.get.return_value = mock_file
    client_mock.models.generate_content.return_value = mock_response

    return client_mock

def test_process_audio_success_flow(s3_client, dynamodb_resource, mock_genai_client):
    """Verifica o fluxo feliz com a nova biblioteca."""
    # ARRANGE
    s3_client.put_object(Bucket=BUCKET_NAME, Key=S3_KEY, Body=b"fake_audio")
    
    table = dynamodb_resource.Table(TABLE_NAME)
    table.put_item(Item={
        "session_id": SESSION_ID,
        "status": "PROCESSING",
        "job_description": "Vaga Python"
    })

    event = {"session_id": SESSION_ID, "bucket": BUCKET_NAME, "key": S3_KEY}
    resources = (s3_client, dynamodb_resource, mock_genai_client)

    # ACT
    result = lambda_handler(event, {}, resources=resources)

    # ASSERT
    assert result["status"] == "COMPLETED"
    
    # Verifica chamadas na NOVA estrutura do SDK
    mock_genai_client.files.upload.assert_called_once()
    mock_genai_client.models.generate_content.assert_called_once()
    
    # Verifica persistência
    item = table.get_item(Key={'session_id': SESSION_ID})['Item']
    assert item['status'] == "COMPLETED"
    assert item['ai_feedback']['technical_score'] == 85

def test_process_audio_handles_ai_error(s3_client, dynamodb_resource, mock_genai_client):
    """Verifica tratamento de erro da IA."""
    # ARRANGE
    s3_client.put_object(Bucket=BUCKET_NAME, Key=S3_KEY, Body=b"silence")
    table = dynamodb_resource.Table(TABLE_NAME)
    table.put_item(Item={"session_id": SESSION_ID, "status": "PROCESSING"})

    # Simula erro de negócio (JSON de erro)
    mock_response = MagicMock()
    mock_response.text = json.dumps({"error": "AUDIO_INAUDIVEL"})
    mock_genai_client.models.generate_content.return_value = mock_response

    resources = (s3_client, dynamodb_resource, mock_genai_client)
    event = {"session_id": SESSION_ID, "bucket": BUCKET_NAME, "key": S3_KEY}

    # ACT
    lambda_handler(event, {}, resources=resources)

    # ASSERT
    item = table.get_item(Key={'session_id': SESSION_ID})['Item']
    assert item['status'] == "ERROR"
    assert item['error_message'] == "AUDIO_INAUDIVEL"

def test_process_audio_missing_file(s3_client, dynamodb_resource, mock_genai_client):
    """Verifica erro de arquivo inexistente no S3."""
    resources = (s3_client, dynamodb_resource, mock_genai_client)
    event = {"session_id": SESSION_ID, "bucket": BUCKET_NAME, "key": S3_KEY}

    with pytest.raises(Exception) as excinfo:
        lambda_handler(event, {}, resources=resources)
    
    assert "404" in str(excinfo.value) or "HeadObject" in str(excinfo.value)