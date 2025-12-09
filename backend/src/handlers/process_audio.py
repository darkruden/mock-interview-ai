import json
import os
import boto3
import google.generativeai as genai
from botocore.config import Config
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
    
    # 1. Leitura Direta (Sem loop de Records)
    session_id = event.get('session_id')
    bucket_name = event.get('bucket')
    s3_key = event.get('key')

    if not session_id or not bucket_name or not s3_key:
        raise ValueError("Payload inválido: Faltam dados obrigatórios (session_id, bucket, key)")

    local_path = f"/tmp/{session_id}.mp3"

    try:
        # [Mantém a lógica original de leitura do banco para Contexto]
        db_response = table.get_item(Key={'session_id': session_id})
        job_description = db_response.get('Item', {}).get('job_description', "")
        
        # Atualiza status para PROCESSING (Caso a Step Function ainda não tenha feito)
        update_status(session_id, "PROCESSING")

        # 2. Download (Igual ao anterior)
        print(f"Baixando de {bucket_name}/{s3_key}...")
        s3_client.download_file(bucket_name, s3_key, local_path)
        
        # ... [MANTENHA O CÓDIGO DO GEMINI E UPDATE_ITEM AQUI IGUAL AO ANTERIOR] ...
        # (O trecho que envia para o Gemini, gera o prompt e salva no DynamoDB não muda)
        
        # Retorno para a Step Function (Opcional, mas boa prática)
        return {
            "status": "COMPLETED",
            "session_id": session_id
        }

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}")
        # Na arquitetura Step Functions, nós lançamos o erro (raise) 
        # para que a State Machine saiba que falhou e possa tentar de novo (Retry)
        raise e 
    
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

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