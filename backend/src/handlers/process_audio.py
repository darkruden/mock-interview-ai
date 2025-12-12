import json
import os
import boto3
from google import genai
from google.genai import types
import time
import tempfile

# --- Padrão Singleton para Clientes ---
_S3_CLIENT = None
_DYNAMODB_RES = None
_GENAI_CLIENT = None

def get_resources():
    global _S3_CLIENT, _DYNAMODB_RES, _GENAI_CLIENT
    
    if _S3_CLIENT is None:
        _S3_CLIENT = boto3.client("s3")
    
    if _DYNAMODB_RES is None:
        _DYNAMODB_RES = boto3.resource("dynamodb")
        
    if _GENAI_CLIENT is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            # A nova lib instancia um Client
            _GENAI_CLIENT = genai.Client(api_key=api_key)
            
    return _S3_CLIENT, _DYNAMODB_RES, _GENAI_CLIENT

def lambda_handler(event, context, resources=None):
    """
    Executa a análise de IA usando o novo SDK google-genai (v1.0+).
    """
    print(f"Worker Iniciado. Payload: {json.dumps(event)}")
    
    s3, db, ai_client = resources if resources else get_resources()
    
    table_name = os.environ.get("TABLE_NAME")
    table = db.Table(table_name)
    
    # 1. Leitura Direta
    session_id = event.get('session_id')
    bucket_name = event.get('bucket')
    s3_key = event.get('key')

    if not session_id or not bucket_name or not s3_key:
        raise ValueError("Payload inválido: Faltam dados obrigatórios")

    local_path = os.path.join(tempfile.gettempdir(), f"{session_id}.mp3")

    try:
        # 2. Busca Contexto
        db_response = table.get_item(Key={'session_id': session_id})
        job_description = db_response.get('Item', {}).get('job_description', "")
        
        # Helper interno para atualizar status
        def _update_status(sid, status, error_msg=None):
            params = {
                'Key': {'session_id': sid},
                'UpdateExpression': "SET #s = :status",
                'ExpressionAttributeNames': {'#s': 'status'},
                'ExpressionAttributeValues': {':status': status}
            }
            if error_msg:
                params['UpdateExpression'] += ", error_message = :err"
                params['ExpressionAttributeValues'][':err'] = error_msg
            table.update_item(**params)
        
        _update_status(session_id, "PROCESSING")

        # 3. Download do S3
        print(f"Baixando de {bucket_name}/{s3_key} para {local_path}...")
        s3.download_file(bucket_name, s3_key, local_path)
        
        # 4. Enviar para Gemini (Nova Sintaxe)
        print("Enviando arquivo para o Gemini...")
        
        # Upload agora é via client.files
        myfile = ai_client.files.upload(file=local_path)
        
        # Polling de processamento
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            # Get file agora é via client.files.get
            myfile = ai_client.files.get(name=myfile.name)

        if myfile.state.name == "FAILED":
            raise ValueError("O processamento do arquivo de áudio falhou no Gemini.")

        # 5. Montagem do Prompt
        base_prompt = """
        Você é um Recrutador Técnico Sênior.
        Sua tarefa é analisar o áudio fornecido.
        """

        context_instruction = ""
        if job_description:
            context_instruction = f"""
            CONTEXTO DA VAGA:
            "{job_description}"
            Avalie se o candidato demonstra os conhecimentos exigidos.
            """

        prompt = f"""
        {base_prompt}
        {context_instruction}

        REGRAS CRÍTICAS:
        1. Analise APENAS o áudio.
        2. Se silêncio/ruído, retorne {{"error": "AUDIO_INAUDIVEL"}}.

        Formato de Resposta (JSON Puro):
        {{
            "technical_score": (0-100),
            "summary": "Resumo",
            "feedback": "Feedback"
        }}
        """
        
        print("Gerando conteúdo...")
        # Geração agora é via client.models.generate_content
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            contents=[myfile, prompt]
        )
        
        response_text = response.text.replace("```json", "").replace("```", "").strip()
        ai_data = json.loads(response_text)

        # 6. Salvar Resultado
        if "error" in ai_data:
             _update_status(session_id, "ERROR", ai_data["error"])
        else:
            table.update_item(
                Key={'session_id': session_id},
                UpdateExpression="SET #s = :status, ai_feedback = :feedback, updated_at = :time",
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':status': 'COMPLETED',
                    ':feedback': ai_data,
                    ':time': str(int(time.time()))
                }
            )

        return {"status": "COMPLETED", "session_id": session_id}

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}")
        raise e 
    
    finally:
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass