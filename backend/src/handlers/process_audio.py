import json
import os
import boto3
import google.generativeai as genai
import time

# --- Configurações ---
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME")
table = dynamodb.Table(TABLE_NAME)

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

def lambda_handler(event, context):
    """
    Executa a análise de IA.
    Espera receber payload direto da Step Function:
    { "session_id": "...", "bucket": "...", "key": "..." }
    """
    print(f"Worker Iniciado. Payload: {json.dumps(event)}")
    
    # 1. Leitura Direta (Payload da Step Function)
    session_id = event.get('session_id')
    bucket_name = event.get('bucket')
    s3_key = event.get('key')

    if not session_id or not bucket_name or not s3_key:
        raise ValueError("Payload inválido: Faltam dados obrigatórios")

    local_path = f"/tmp/{session_id}.mp3"

    try:
        # 2. Busca Contexto (Job Description)
        db_response = table.get_item(Key={'session_id': session_id})
        job_description = db_response.get('Item', {}).get('job_description', "")
        
        # Avisa que começou (útil para debug)
        update_status(session_id, "PROCESSING")

        # 3. Download do Áudio
        print(f"Baixando de {bucket_name}/{s3_key}...")
        s3_client.download_file(bucket_name, s3_key, local_path)
        
        # 4. Enviar para Gemini
        print("Enviando arquivo para o Gemini...")
        myfile = genai.upload_file(local_path)
        
        # Espera o Gemini processar o arquivo internamente
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = genai.get_file(myfile.name)

        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # 5. Montagem do Prompt com Contexto
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
            
            Avalie se o candidato demonstra os conhecimentos exigidos na descrição acima.
            Se ele fugir do tema da vaga, penalize a nota técnica.
            """

        prompt = f"""
        {base_prompt}
        {context_instruction}

        REGRAS CRÍTICAS (ANTI-ALUCINAÇÃO):
        1. Você deve analisar APENAS o que ouvir neste áudio específico.
        2. Se o áudio for silêncio, ruído ou inaudível, retorne o JSON com "error": "AUDIO_INAUDIVEL".
        3. Se o candidato falar pouco, analise apenas o pouco que ele disse.

        Formato de Resposta (JSON Puro):
        {{
            "technical_score": (0-100),
            "clarity_score": (0-100),
            "summary": "Resumo fiel do que foi dito",
            "strengths": ["Ponto forte 1"],
            "weaknesses": ["Ponto fraco 1"],
            "feedback": "Feedback construtivo focado na vaga (se houver)"
        }}
        """
        
        print("Gerando conteúdo com a IA...")
        result = model.generate_content([myfile, prompt])
        
        # Limpeza do JSON
        response_text = result.text.replace("```json", "").replace("```", "").strip()
        print(f"Resposta da IA: {response_text}")
        
        ai_data = json.loads(response_text)

        # 6. Salvar no DynamoDB (O passo que estava faltando!)
        if "error" in ai_data:
             update_status(session_id, "ERROR", ai_data["error"])
        else:
            print("Salvando feedback no DynamoDB...")
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

        return {
            "status": "COMPLETED",
            "session_id": session_id
        }

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}")
        # Importante: Lançar o erro para a Step Function saber que falhou
        raise e 
    
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
            print("Limpeza concluída.")

def update_status(session_id, status, error_msg=None):
    params = {
        'Key': {'session_id': session_id},
        'UpdateExpression': "SET #s = :status",
        'ExpressionAttributeNames': {'#s': 'status'},
        'ExpressionAttributeValues': {':status': status}
    }
    if error_msg:
        params['UpdateExpression'] += ", error_message = :err"
        params['ExpressionAttributeValues'][':err'] = error_msg
    table.update_item(**params)