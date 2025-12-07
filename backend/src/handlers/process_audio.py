import json
import os
import boto3
import google.generativeai as genai
from botocore.config import Config
import time

# --- Configurações ---
# O Lambda tem um disco temporário em /tmp. Usaremos para manipular o áudio.
TEMP_PATH = "/tmp/audio_file.mp3"

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME")
table = dynamodb.Table(TABLE_NAME)

# Configura a IA
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

def lambda_handler(event, context):
    """
    Acionada automaticamente quando um arquivo cai no S3.
    """
    print(f"Evento S3 Recebido: {json.dumps(event)}")
    
    for record in event['Records']:
        try:
            # 1. Extrair detalhes do evento S3
            bucket_name = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']
            
            # O s3_key é algo como: uploads/SESSION_ID/audio.mp3
            # Vamos extrair o SESSION_ID
            session_id = s3_key.split("/")[1]
            
            print(f"Processando Sessão: {session_id}")

            # 2. Atualizar status para PROCESSING
            update_status(session_id, "PROCESSING")

            # 3. Baixar o áudio do S3 para o disco local da Lambda
            s3_client.download_file(bucket_name, s3_key, TEMP_PATH)
            print("Áudio baixado com sucesso.")

            # 4. Enviar para o Gemini (Multimodal)
            # O Gemini 2.5 Flash ouve áudio nativamente!
            print("Enviando para o Gemini...")
            myfile = genai.upload_file(TEMP_PATH)
            
            # Aguarda o processamento do arquivo no lado do Google
            while myfile.state.name == "PROCESSING":
                print("Gemini processando o arquivo de áudio...")
                time.sleep(1)
                myfile = genai.get_file(myfile.name)

            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # O Prompt de Engenharia (A "Alma" do Recrutador)
            prompt = """
            Você é um Recrutador Técnico Sênior. Ouça o áudio com atenção.
            
            PASSO 1: Verificação de Áudio
            - Se o áudio estiver mudo, silencioso ou inaudível, retorne um JSON com o campo "error": "SILENCE_DETECTED" e pare.
            
            PASSO 2: Análise (Apenas se houver fala)
            - Analise a resposta do candidato.
            - Retorne o JSON neste formato:
            {
                "technical_score": (0-100),
                "clarity_score": (0-100),
                "summary": "Resumo...",
                "feedback": "Feedback..."
            }
            """
            
            result = model.generate_content([myfile, prompt])
            response_text = result.text.replace("```json", "").replace("```", "").strip()
            
            print(f"Resposta da IA: {response_text}")
            ai_data = json.loads(response_text)

            # 5. Salvar resultado (Smart Data) e Finalizar
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
            print("DynamoDB atualizado com sucesso!")

        except Exception as e:
            print(f"ERRO FATAL na sessão {session_id if 'session_id' in locals() else 'unknown'}: {str(e)}")
            if 'session_id' in locals():
                update_status(session_id, "ERROR", str(e))
            raise e # Lança o erro para a AWS tentar de novo (Retry)

def update_status(session_id, status, error_msg=None):
    """Função auxiliar para atualizar apenas o status"""
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