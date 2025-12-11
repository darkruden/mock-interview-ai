import pytest
from unittest.mock import MagicMock
from handlers.start_execution import lambda_handler
import os

def test_trigger_step_function_success():
    """Verifica se a Step Function é iniciada com o payload correto."""
    # Arrange
    os.environ["STATE_MACHINE_ARN"] = "arn:aws:states:us-east-1:123:stateMachine:TestWF"
    mock_sfn = MagicMock()
    
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "uploads/uuid-1234/audio.mp3"}
            }
        }]
    }
    
    # Mock do context (precisamos do aws_request_id)
    mock_context = MagicMock()
    mock_context.aws_request_id = "request-9999"

    # Act
    response = lambda_handler(event, mock_context, sfn_client=mock_sfn)

    # Assert
    assert response["statusCode"] == 200
    
    # Verifica se start_execution foi chamado com os argumentos certos
    mock_sfn.start_execution.assert_called_once()
    
    # Verifica o payload enviado para a Step Function
    call_args = mock_sfn.start_execution.call_args[1]
    assert call_args['stateMachineArn'] == os.environ["STATE_MACHINE_ARN"]
    assert '"session_id": "uuid-1234"' in call_args['input']
    assert '"bucket": "test-bucket"' in call_args['input']

def test_ignore_invalid_key_structure():
    """Arquivos na raiz ou pastas erradas não devem disparar a SF."""
    mock_sfn = MagicMock()
    event = {
        "Records": [{"s3": {"bucket": {"name": "b"}, "object": {"key": "arquivo_solto.mp3"}}}]
    }
    
    lambda_handler(event, MagicMock(), sfn_client=mock_sfn)
    
    mock_sfn.start_execution.assert_not_called()