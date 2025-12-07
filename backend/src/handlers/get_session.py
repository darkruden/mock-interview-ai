import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_NAME")
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """Corrige o erro de Decimal do DynamoDB na hora de converter pra JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    print(f"Evento recebido: {json.dumps(event)}")
    
    try:
        # Pega o ID da URL (ex: /sessions/123-abc)
        session_id = event.get('pathParameters', {}).get('session_id')
        
        if not session_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing session_id"})}

        response = table.get_item(Key={'session_id': session_id})
        
        if 'Item' not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Session not found"})}

        item = response['Item']
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*" # CORS
            },
            "body": json.dumps(item, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Erro: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}