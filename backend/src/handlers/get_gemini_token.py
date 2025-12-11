import json
import os

# Nenhuma dependência externa complexa além de variável de ambiente
def lambda_handler(event, context):
    """
    Retorna a chave de API do Gemini para o frontend.
    TODO: Em produção real, gerar um token efêmero ou assinado.
    Por enquanto, proxy simples da variável de ambiente.
    """
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada no servidor.")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "token": api_key
            })
        }

    except Exception as e:
        print(f"Erro ao obter token: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }