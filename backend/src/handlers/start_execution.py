import json
import os
import boto3
import urllib.parse

# Cliente da Step Functions
sfn_client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

def lambda_handler(event, context):
    """
    Gatilho S3: Recebe o upload e inicia a State Machine.
    """
    print(f"S3 Event recebido: {json.dumps(event)}")

    if not STATE_MACHINE_ARN:
        print("ERRO: STATE_MACHINE_ARN não configurado.")
        return

    # Pode haver múltiplos arquivos num só evento, processamos todos
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        # Decodifica o nome do arquivo (ex: espaços viram %20)
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        # Extrai o session_id do caminho (uploads/UUID/audio.mp3)
        try:
            session_id = key.split("/")[1]
        except IndexError:
            print(f"Ignorando arquivo fora do padrão: {key}")
            continue

        # Payload que será enviado para a Step Function -> e depois para o process_audio.py
        input_payload = {
            "session_id": session_id,
            "bucket": bucket,
            "key": key,
            "timestamp": record['eventTime']
        }

        try:
            response = sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f"analysis-{session_id}", # Nome único da execução (Evita duplicidade)
                input=json.dumps(input_payload)
            )
            print(f"Started execution: {response['executionArn']}")
        except sfn_client.exceptions.ExecutionAlreadyExists:
            print(f"Execução já existe para a sessão {session_id}")
        except Exception as e:
            print(f"Erro ao iniciar Step Function: {str(e)}")
            raise e

    return {"status": "triggered"}