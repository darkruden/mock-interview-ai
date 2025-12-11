import json
import os
import boto3
import google.generativeai as genai
import time
import tempfile  # <--- IMPORTANTE: Adicione esta importação

# --- Padrão Singleton para Clientes ---
_S3_CLIENT = None
_DYNAMODB_RES = None
_GENAI_CONFIGURED = False

def get_resources():
    global _S3_CLIENT, _DYNAMODB_RES, _GENAI_CONFIGURED
    
    if _S3_CLIENT is None:
        _S3_CLIENT = boto3.client("s3")
    
    if _DYNAMODB_RES is None:
        _DYNAMODB_RES = boto3.resource("dynamodb")
        
    if not _GENAI_CONFIGURED:
        GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
        if GEMINI_KEY:
            genai.configure(api_key=GEMINI_KEY)
            _GENAI_CONFIGURED = True
            
    return _S3_CLIENT, _DYNAMODB_RES, genai

def lambda_handler(event, context, resources=None):
    """
    Executa a análise de IA com suporte a injeção de dependência e OS agnóstico.
    """
    print(f"Worker Iniciado. Payload: {json.dumps(event)}")
    
    s3, db, ai_module = resources if resources else get_resources()
    
    table_name = os.environ.get("TABLE_NAME")
    table = db.Table(table_name)
    
    # 1. Leitura Direta
    session_id = event.get('session_id')
    bucket_name = event.get('bucket')
    s3_key = event.get('key')

    if not session_id or not bucket_name or not s3_key:
        raise ValueError("Payload inválido: Faltam dados obrigatórios")

    # --- CORREÇÃO CRÍTICA AQUI ---
    # Em vez de hardcoded '/tmp/', usamos o diretório temporário do sistema
    local_path = os.path.join(tempfile.gettempdir(), f"{session_id}.mp3")
    # -----------------------------

    try:
        # 2. Busca Contexto (Job Description)
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

        # 3. Download do Áudio
        print(f"Baixando de {bucket_name}/{s3_key} para {local_path}...")
        s3.download_file(bucket_name, s3_key, local_path)
        
        # 4. Enviar para Gemini
        print("Enviando arquivo para o Gemini...")
        myfile = ai_module.upload_file(local_path)
        
        while myfile.state.name == "PROCESSING":
            time.sleep(0.5)
            myfile = ai_module.get_file(myfile.name)

        model = ai_module.GenerativeModel("gemini-2.5-flash")
        
        # 5. Montagem do Prompt
        base_prompt = """
        Você é um Recrutador Técnico Sênior e Auditor.
        Sua tarefa é analisar o áudio fornecido.
        """

        context_instruction = ""
        if job_description:
            context_instruction = f"""
            CONTEXTO DA VAGA (IMPORTANTE):
            O candidato está se aplicando para a seguinte vaga:
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
        
        result = model.generate_content([myfile, prompt])
        
        response_text = result.text.replace("```json", "").replace("```", "").strip()
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
        # Garante a limpeza independente do SO
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                print("Limpeza concluída.")
            except Exception as clean_err:
                print(f"Erro na limpeza: {clean_err}")