import json
import os
from handlers.get_gemini_token import lambda_handler

def test_return_token_successfully():
    # Arrange
    os.environ["GEMINI_API_KEY"] = "secret_key_123"
    
    # Act
    response = lambda_handler({}, {})
    body = json.loads(response["body"])
    
    # Assert
    assert response["statusCode"] == 200
    assert body["token"] == "secret_key_123"

def test_handle_missing_env_var():
    # Arrange
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
        
    # Act
    response = lambda_handler({}, {})
    
    # Assert
    assert response["statusCode"] == 500
    assert "error" in response["body"]