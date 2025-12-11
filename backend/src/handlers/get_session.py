import json
import os
import boto3
from botocore.config import Config
from decimal import Decimal

# Singleton para conexão
_DYNAMODB_RES = None

# Classe auxiliar para converter Decimal do DynamoDB para JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def get_db():
    global _DYNAMODB_RES
    if _DYNAMODB_RES is None:
        config = Config(retries={'max_attempts': 3, 'mode': 'standard'})
        _DYNAMODB_RES = boto3.resource("dynamodb", config=config)
    return _DYNAMODB_RES

def lambda_handler(event, context, dynamodb_resource=None):
    """
    Busca o status e feedback da sessão.
    Rota: GET /session/{session_id}
    """
    # Injeção de dependência para testes
    db = dynamodb_resource if dynamodb_resource else get_db()
    
    TABLE_NAME = os.environ.get("TABLE_NAME")
    table = db.Table(TABLE_NAME)

    # Pegar ID da URL (pathParameters)
    session_id = None
    if event.get("pathParameters"):
        session_id = event["pathParameters"].get("session_id")
    
    if not session_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing session_id"})
        }

    try:
        response = table.get_item(Key={'session_id': session_id})
        
        if 'Item' not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Session not found"})
            }

        item = response['Item']
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            # Usa o Encoder customizado para lidar com números do DynamoDB
            "body": json.dumps(item, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }