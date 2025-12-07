import json
import uuid
import os
import boto3
from botocore.config import Config

# Configuração para reduzir tempo de conexão (Cold Start mitigation)
boto_config = Config(retries={'max_attempts': 3, 'mode': 'standard'})

# Inicializa clientes fora do handler (Reaproveitamento de conexão)
s3_client = boto3.client("s3", config=boto_config)
dynamodb = boto3.resource("dynamodb", config=boto_config)

# Variáveis de ambiente (serão injetadas pelo Terraform)
BUCKET_NAME = os.environ.get("BUCKET_NAME")
TABLE_NAME = os.environ.get("TABLE_NAME")
sessions_table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Gera uma Presigned URL para upload direto no S3 e inicia a sessão no DynamoDB.
    """
    print(f"Evento Recebido: {json.dumps(event)}")

    try:
        # 1. Parsing do Input
        body = {}
        if event.get("body"):
            body = json.loads(event["body"])
        
        candidate_name = body.get("candidate_name", "Anonymous")
        question_id = body.get("question_id", "Q1")

        # 2. Gerar ID Único da Sessão
        session_id = str(uuid.uuid4())
        object_key = f"uploads/{session_id}/audio.mp3"

        # 3. Persistir Estado Inicial (Smart Data Traceability)
        # Registramos que a intenção de upload existiu
        sessions_table.put_item(
            Item={
                "session_id": session_id,
                "status": "PENDING_UPLOAD",
                "candidate_name": candidate_name,
                "question_id": question_id,
                "s3_key": object_key,
                # Expira em 24h (TTL)
                "expire_at": int(os.times().elapsed + 86400) 
            }
        )

        # 4. Gerar URL Assinada (O "Crachá" de acesso)
        # Válida por 5 minutos (300 segundos)
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': object_key,
                'ContentType': 'audio/mpeg' # Força ser um arquivo de áudio
            },
            ExpiresIn=300
        )

        # 5. Retorno
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" # CORS
            },
            "body": json.dumps({
                "message": "Upload session initiated",
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