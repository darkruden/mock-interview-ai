import boto3
import json
import time
import os
import requests
import wave
import struct
import sys
from decimal import Decimal # <--- Importante para corrigir o erro

# --- CONFIGURAÇÃO ---
FUNCTION_GET_URL = "mock-interview-get-upload-url-dev"
TABLE_NAME = "mock-interview-sessions-dev"
REGION = "us-east-1"
FILE_TO_UPLOAD = "test_audio.mp3"

# Classe mágica para converter Decimal do DynamoDB em JSON legível
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) # Converte Decimal para Float normal
        return super(DecimalEncoder, self).default(obj)

def create_dummy_audio():
    """Cria um arquivo de áudio válido (WAV renomeado) de 1 segundo para teste"""
    if os.path.exists(FILE_TO_UPLOAD):
        return
    
    print("🎤 Criando arquivo de áudio de teste (dummy)...")
    with wave.open(FILE_TO_UPLOAD, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        data = struct.pack('<h', 0) * 44100
        wav_file.writeframes(data)

def run_e2e_test():
    print(f"🚀 INICIANDO TESTE END-TO-END")
    print(f"--------------------------------------------------")
    
    # 0. Setup
    create_dummy_audio()
    lambda_client = boto3.client("lambda", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    # 1. Obter URL de Upload (Handshake)
    print("\n1️⃣  Solicitando URL de Upload...")
    payload = {"body": json.dumps({"candidate_name": "E2E Tester"})}
    try:
        response = lambda_client.invoke(
            FunctionName=FUNCTION_GET_URL,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        api_resp = json.loads(response['Payload'].read())
    except Exception as e:
        print(f"❌ Erro ao invocar Lambda: {e}")
        return

    if api_resp.get("statusCode") != 201:
        print(f"❌ Erro na API: {api_resp}")
        return
    
    body = json.loads(api_resp["body"])
    session_id = body["session_id"]
    upload_url = body["upload_url"]
    print(f"   ✅ Sessão criada: {session_id}")

    # 2. Fazer Upload para o S3 (Direct-to-Cloud)
    print("\n2️⃣  Enviando arquivo para o S3 (PUT)...")
    with open(FILE_TO_UPLOAD, 'rb') as f:
        http_resp = requests.put(upload_url, data=f, headers={'Content-Type': 'audio/mpeg'})
    
    if http_resp.status_code == 200:
        print("   ✅ Upload concluído com sucesso!")
    else:
        print(f"   ❌ Falha no upload: {http_resp.status_code} - {http_resp.text}")
        return

    # 3. Polling (Esperar a IA processar)
    print("\n3️⃣  Aguardando processamento da IA (Polling DynamoDB)...")
    
    for i in range(30): # Tenta por ~60 segundos
        response = table.get_item(Key={'session_id': session_id})
        item = response.get('Item', {})
        status = item.get('status')
        
        sys.stdout.write(f"\r   ⏳ Status atual: {status} " + ("." * (i % 4)) + "   ")
        sys.stdout.flush()
        
        if status == 'COMPLETED':
            print("\n\n🎉 PROCESSAMENTO CONCLUÍDO!")
            print("--------------------------------------------------")
            print(f"📄 Feedback da IA (Gemini):")
            
            # AQUI ESTAVA O ERRO: Agora usamos o cls=DecimalEncoder
            print(json.dumps(item.get('ai_feedback'), indent=2, ensure_ascii=False, cls=DecimalEncoder))
            
            print("--------------------------------------------------")
            return
        elif status == 'ERROR':
            print(f"\n❌ Erro no processamento: {item.get('error_message')}")
            return
        
        time.sleep(2)

    print("\n⚠️ Timeout: O processamento demorou muito.")

if __name__ == "__main__":
    run_e2e_test()