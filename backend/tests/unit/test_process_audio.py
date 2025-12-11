import pytest
import json
from unittest.mock import MagicMock
from handlers.process_audio import lambda_handler

# Dados de teste reutilizáveis
SESSION_ID = "test-session-123"
BUCKET_NAME = "mock-interview-tests-bucket"
S3_KEY = f"uploads/{SESSION_ID}/audio.mp3"
TABLE_NAME = "MockInterviewSessions-Test"

@pytest.fixture
def mock_genai():
    """
    Cria um simulacro (Mock) completo do Google Gemini SDK.
    Isso engana o handler fazendo-o achar que está falando com a IA real.
    """
    # 1. Mock do objeto 'File' retornado pelo upload
    mock_file = MagicMock()
    mock_file.state.name = "ACTIVE" # Simula que o arquivo processou rápido
    mock_file.name = "files/123"

    # 2. Mock do Modelo Generativo
    mock_model = MagicMock()
    
    # 3. Mock da resposta da geração de conteúdo
    mock_response = MagicMock()
    # Simula o JSON que o Gemini retornaria na vida real
    mock_response.text = json.dumps({
        "technical_score": 85,
        "clarity_score": 90,
        "summary": "O candidato explicou bem sobre AWS Lambda.",
        "strengths": ["Boa dicção", "Conhecimento técnico"],
        "weaknesses": ["Poderia ser mais direto"],
        "feedback": "Boa resposta.",
        "follow_up_question": "Como você lidaria com Cold Starts?"
    })
    
    mock_model.generate_content.return_value = mock_response

    # 4. Monta o objeto principal 'genai'
    genai_mock = MagicMock()
    genai_mock.upload_file.return_value = mock_file
    genai_mock.get_file.return_value = mock_file
    genai_mock.GenerativeModel.return_value = mock_model

    return genai_mock

def test_process_audio_success_flow(s3_client, dynamodb_resource, mock_genai):
    """
    Cenário: O processamento ocorre perfeitamente.
    Verifica:
    1. Se o áudio foi baixado do S3.
    2. Se o Gemini foi chamado com o prompt correto.
    3. Se o resultado foi salvo no DynamoDB com status COMPLETED.
    """
    # --- ARRANGE (Preparação) ---
    # 1. Criar o cenário no "Banco de Dados Falso" e "S3 Falso"
    s3_client.put_object(Bucket=BUCKET_NAME, Key=S3_KEY, Body=b"fake_audio_content")
    
    table = dynamodb_resource.Table(TABLE_NAME)
    table.put_item(Item={
        "session_id": SESSION_ID,
        "status": "PROCESSING", # Simula estado anterior
        "job_description": "Vaga de Python Developer Sênior"
    })

    # 2. Montar o payload que viria da Step Functions
    event = {
        "session_id": SESSION_ID,
        "bucket": BUCKET_NAME,
        "key": S3_KEY
    }

    # 3. Pacote de recursos injetados (Dependency Injection)
    resources = (s3_client, dynamodb_resource, mock_genai)

    # --- ACT (Execução) ---
    result = lambda_handler(event, {}, resources=resources)

    # --- ASSERT (Validação) ---
    assert result["status"] == "COMPLETED"
    
    # Verifica se salvou no banco
    updated_item = table.get_item(Key={'session_id': SESSION_ID})['Item']
    
    assert updated_item['status'] == "COMPLETED"
    assert "ai_feedback" in updated_item
    assert updated_item['ai_feedback']['technical_score'] == 85
    
    # Verifica se o Gemini recebeu o contexto da vaga no prompt
    # (Acessamos o histórico de chamadas do mock)
    _, call_kwargs = mock_genai.GenerativeModel().generate_content.call_args
    # O prompt é o segundo argumento da lista passada para generate_content([file, prompt])
    # Como o mock armazena args posicionalmente, acessamos args[0][1]
    prompt_sent = mock_genai.GenerativeModel().generate_content.call_args[0][0][1]
    
    assert "Vaga de Python Developer Sênior" in prompt_sent
    assert "Recrutador Técnico Sênior" in prompt_sent

def test_process_audio_handles_ai_error(s3_client, dynamodb_resource, mock_genai):
    """
    Cenário: A IA identifica que o áudio é inaudível.
    Verifica: Se o sistema atualiza o status para ERROR sem quebrar.
    """
    # --- ARRANGE ---
    s3_client.put_object(Bucket=BUCKET_NAME, Key=S3_KEY, Body=b"silence")
    table = dynamodb_resource.Table(TABLE_NAME)
    table.put_item(Item={"session_id": SESSION_ID, "status": "PROCESSING"})

    # Simula resposta de erro da IA (conforme suas regras de prompt)
    mock_response = MagicMock()
    mock_response.text = json.dumps({"error": "AUDIO_INAUDIVEL"})
    mock_genai.GenerativeModel().generate_content.return_value = mock_response

    resources = (s3_client, dynamodb_resource, mock_genai)
    event = {"session_id": SESSION_ID, "bucket": BUCKET_NAME, "key": S3_KEY}

    # --- ACT ---
    # A função não deve lançar exceção, mas sim tratar o erro de negócio
    lambda_handler(event, {}, resources=resources)

    # --- ASSERT ---
    updated_item = table.get_item(Key={'session_id': SESSION_ID})['Item']
    assert updated_item['status'] == "ERROR"
    assert updated_item['error_message'] == "AUDIO_INAUDIVEL"

def test_process_audio_missing_file(s3_client, dynamodb_resource, mock_genai):
    """
    Cenário: O arquivo não está no S3 (Edge Case).
    Verifica: Se lança exceção para a Step Function tentar novamente ou falhar.
    """
    # Não criamos o arquivo no S3 propositalmente
    resources = (s3_client, dynamodb_resource, mock_genai)
    event = {"session_id": SESSION_ID, "bucket": BUCKET_NAME, "key": S3_KEY}

    # Esperamos que o boto3 lance um ClientError (404 Not Found)
    with pytest.raises(Exception) as excinfo:
        lambda_handler(event, {}, resources=resources)
    
    # O erro deve vir do S3 (HeadObject ou Download)
    assert "HeadObject" in str(excinfo.value) or "404" in str(excinfo.value)