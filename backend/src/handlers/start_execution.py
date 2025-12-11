import json
import os
import boto3
import urllib.parse
from botocore.config import Config

_SFN_CLIENT = None

def get_sfn_client():
    global _SFN_CLIENT
    if _SFN_CLIENT is None:
        config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
        _SFN_CLIENT = boto3.client("stepfunctions", config=config)
    return _SFN_CLIENT

def lambda_handler(event, context, sfn_client=None):
    """
    Trigger S3 -> Step Functions.
    Inicia o fluxo de orquestração quando um arquivo é salvo.
    """
    client = sfn_client if sfn_client else get_sfn_client()
    state_machine_arn = os.environ.get("STATE_MACHINE_ARN")

    print(f"Evento Recebido: {json.dumps(event)}")

    try:
        # Processa cada arquivo (geralmente é um só, mas S3 pode enviar lotes)
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            # Extrai o session_id do caminho (uploads/{uuid}/audio.mp3)
            # Estrutura esperada: uploads/<session_id>/arquivo
            parts = key.split('/')
            if len(parts) < 2:
                print(f"Ignorando chave inválida: {key}")
                continue
                
            session_id = parts[1]

            input_payload = {
                "session_id": session_id,
                "bucket": bucket,
                "key": key
            }

            print(f"Iniciando Step Function para sessão: {session_id}")
            
            client.start_execution(
                stateMachineArn=state_machine_arn,
                name=f"{session_id}-{int(context.aws_request_id[-4:])}", # Nome único da execução
                input=json.dumps(input_payload)
            )

        return {"statusCode": 200, "body": "Execution Started"}

    except Exception as e:
        print(f"ERRO: {str(e)}")
        # Não lançamos erro para não reprocessar eventos do S3 infinitamente em loop
        return {"statusCode": 500, "error": str(e)}