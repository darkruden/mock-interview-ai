import json
import uuid
import os
import time
import boto3
from botocore.config import Config

# Configuração para reduzir tempo de conexão (Cold Start mitigation)
boto_config = Config(retries={'max_attempts': 3, 'mode': 'standard'})

# Inicializa clientes fora do handler
s3_client = boto3.client("s3", config=boto_config)
dynamodb = boto3.resource("dynamodb", config=boto_config)

BUCKET_NAME = os.environ.get("BUCKET_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
sessions_table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Inicia sessão, recebe contexto da vaga e gera URL de upload.
    """
    print(f"Evento Recebido: {json.dumps(event)}")

    try:
        # 1. Parsing do Input
        body = {}
        if event.get("body"):
            body = json.loads(event["body"])
        
        # --- NOVO: Captura a descrição da vaga (pode ser vazio) ---
        job_description = body.get("job_description", "")
        # Limita caracteres para não explodir o banco (segurança básica)
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
            # --- NOVO: Salva o contexto no banco ---
            "job_description": job_description 
        }

        sessions_table.put_item(Item=item)

        # 4. Gerar URL Assinada
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': BUCKET_NAME,
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