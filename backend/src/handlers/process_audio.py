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
    print(f"Evento S3 Recebido: {json.dumps(event)}")
    
    for record in event['Records']:
        local_path = ""
        try:
            bucket_name = record['s3']['bucket']['name']
            s3_key = record['s3']['object']['key']
            
            # Extrair Session ID
            session_id = s3_key.split("/")[1]
            print(f"Processando Sessão: {session_id}")

            update_status(session_id, "PROCESSING")

            # --- CORREÇÃO 1: NOME DE ARQUIVO ÚNICO ---
            # Evita o "Arquivo Zumbi" de execuções anteriores
            local_path = f"/tmp/{session_id}.mp3"

            # Baixar
            print(f"Baixando de {bucket_name}/{s3_key} para {local_path}...")
            s3_client.download_file(bucket_name, s3_key, local_path)
            
            # Verificar tamanho do arquivo (Debug)
            file_size = os.path.getsize(local_path)
            print(f"Tamanho do arquivo baixado: {file_size} bytes")

            if file_size < 1000: # Se for menor que 1KB, provavelmente é silêncio ou erro
                print("⚠️ AVISO: Arquivo de áudio muito pequeno/vazio.")

            # Enviar para Gemini
            print("Enviando para o Gemini...")
            myfile = genai.upload_file(local_path)
            
            while myfile.state.name == "PROCESSING":
                time.sleep(1)
                myfile = genai.get_file(myfile.name)

            # Usando o modelo V2 (Mais recente)
            model = genai.GenerativeModel("gemini-1.5-flash-002")
            
            # --- CORREÇÃO 2: PROMPT ANTI-ALUCINAÇÃO ---
            prompt = """
            Você é um Recrutador Técnico Sênior e Auditor.
            Sua tarefa é analisar o áudio fornecido.

            REGRAS CRÍTICAS (ANTI-ALUCINAÇÃO):
            1. Você deve analisar APENAS o que ouvir neste áudio específico. NÃO invente tecnologias que o candidato não mencionou.
            2. Se o áudio for silêncio, ruído ou inaudível, retorne o JSON com "error": "AUDIO_INAUDIVEL".
            3. Se o candidato falar pouco, analise apenas o pouco que ele disse. Não "encha linguiça".

            Formato de Resposta (JSON Puro):
            {
                "technical_score": (0-100),
                "clarity_score": (0-100),
                "summary": "Resumo fiel do que foi dito",
                "strengths": ["Ponto forte 1"],
                "weaknesses": ["Ponto fraco 1"],
                "feedback": "Feedback construtivo"
            }
            """
            
            result = model.generate_content([myfile, prompt])
            
            # Limpeza do JSON (remove markdown se a IA colocar)
            response_text = result.text.replace("```json", "").replace("```", "").strip()
            print(f"Resposta da IA: {response_text}")
            
            ai_data = json.loads(response_text)

            # Verifica se a IA detectou erro de áudio
            if "error" in ai_data:
                 update_status(session_id, "ERROR", ai_data["error"])
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

        except Exception as e:
            print(f"ERRO FATAL: {str(e)}")
            if 'session_id' in locals():
                update_status(session_id, "ERROR", f"Internal Error: {str(e)}")
            # Não damos raise para não entrar em loop infinito de retry da Lambda se for erro de lógica
        
        finally:
            # --- CORREÇÃO 3: LIMPEZA ---
            # Apaga o arquivo do disco temporário para não sobrar para a próxima execução
            if os.path.exists(local_path):
                os.remove(local_path)
                print("Arquivo temporário removido.")

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