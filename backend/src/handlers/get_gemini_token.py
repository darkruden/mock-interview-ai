import json
import os
import datetime

# Tentativa de importação segura
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def lambda_handler(event, context):
    print("Iniciando Lambda de Token...")
    
    if genai is None:
        return {"statusCode": 500, "body": json.dumps({"error": "Dependency Error: google-genai not found"})}

    if not GEMINI_API_KEY:
        return {"statusCode": 500, "body": json.dumps({"error": "Missing API Key"})}

    try:
        client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})

        # Token válido por 10 minutos
        expire_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        
        auth_token = client.auth_tokens.create(
            config={
                'expire_time': expire_time,
                'http_options': {'api_version': 'v1alpha'}
            }
        )
        
        # [CORREÇÃO CRÍTICA] Remove o prefixo "authTokens/" se existir
        raw_token = auth_token.name
        if raw_token.startswith("authTokens/"):
            raw_token = raw_token.replace("authTokens/", "")

        print(f"Token gerado (truncado): {raw_token[:10]}...")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            },
            "body": json.dumps({
                "token": raw_token, # Envia o token LIMPO
                "expiration": str(expire_time)
            })
        }

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }