import json
import os
import datetime

# Tentativa de importação segura para debug
try:
    from google import genai
    from google.genai import types
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    # Se der erro aqui, vai aparecer no CloudWatch como ImportError, não HandlerNotFound
    genai = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def lambda_handler(event, context):
    print("Iniciando Lambda de Token...")
    
    # 1. Validação de Dependência
    if genai is None:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Dependency Error: google-genai library not found"})
        }

    # 2. Validação de Chave
    if not GEMINI_API_KEY:
        print("ERRO: GEMINI_API_KEY não encontrada.")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Server Configuration Error: Missing API Key"})
        }

    try:
        # 3. Geração do Token
        client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})

        now = datetime.datetime.now(datetime.timezone.utc)
        # Token válido por 10 minutos
        expire_time = now + datetime.timedelta(minutes=10)
        
        auth_token = client.auth_tokens.create(
            config={
                'expire_time': expire_time,
                'http_options': {'api_version': 'v1alpha'}
            }
        )

        print("Token gerado com sucesso.")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*", # CORS na Lambda também ajuda
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            },
            "body": json.dumps({
                "token": auth_token.name,
                "expiration": str(expire_time)
            })
        }

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to generate token: {str(e)}"})
        }