import json
import uuid
import os
import time
import boto3
from botocore.config import Config

# --- Padrão Singleton para Clientes AWS (Cold Start Mitigation) ---
_S3_CLIENT = None
_DYNAMODB_RES = None

def get_clients():
    """
    Retorna ou inicializa os clientes AWS.
    Permite reutilização da conexão entre invocações da mesma Lambda (Warm Start).
    """
    global _S3_CLIENT, _DYNAMODB_RES
    
    if _S3_CLIENT is None:
        boto_config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
        _S3_CLIENT = boto3.client("s3", config=boto_config)
    
    if _DYNAMODB_RES is None:
        boto_config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
        _DYNAMODB_RES = boto3.resource("dynamodb", config=boto_config)
        
    return _S3_CLIENT, _DYNAMODB_RES

def lambda_handler(event, context, clients=None):
    """
    Handler com suporte a Injeção de Dependência para testes.
    Args:
        clients: Tupla (s3_client, dynamodb_resource) opcional para testes.
    """
    print(f"Evento Recebido: {json.dumps(event)}")

    try:
        # Injeção de Dependência: Se 'clients' for passado (teste), usa ele.
        # Caso contrário (produção), usa o Singleton get_clients().
        s3, db = clients if clients else get_clients()
        
        bucket_name = os.environ.get("BUCKET_NAME")
        table_name = os.environ.get("TABLE_NAME")
        sessions_table = db.Table(table_name)

        # 1. Parsing do Input
        body = {}
        if event.get("body"):
            body = json.loads(event["body"])
        
        job_description = body.get("job_description", "")
        if len(job_description) > 5000:
            job_description = job_description[:5000]

        candidate_name = body.get("candidate_name", "Anonymous")
        question_id = body.get("question_id", "Q1")

        # 2. Gerar ID Único
        session_id = str(uuid.uuid4())
        object_key = f"uploads/{session_id}/audio.mp3"

        # 3. Persistir Estado Inicial
        item = {
            "session_id": session_id,
            "status": "PENDING_UPLOAD",
            "candidate_name": candidate_name,
            "question_id": question_id,
            "s3_key": object_key,
            "expire_at": int(time.time() + 86400),
            "job_description": job_description 
        }

        sessions_table.put_item(Item=item)

        # 4. Gerar URL Assinada
        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key,
                'ContentType': 'audio/mpeg'
            },
            ExpiresIn=300
        )

        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Session initiated",
                "session_id": session_id,
                "upload_url": presigned_url
            })
        }

    except Exception as e:
        print(f"ERRO CRÍTICO: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }