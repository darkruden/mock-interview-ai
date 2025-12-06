import boto3
import json
import sys

# --- CONFIGURAÇÃO ---
# O nome exato da função que criamos no Terraform
FUNCTION_NAME = "mock-interview-get-upload-url-dev"
REGION = "us-east-1"

def run_test():
    print(f"🚀 Iniciando Teste de Handshake na função: {FUNCTION_NAME}...")
    
    # 1. Configurar Clientes AWS
    lambda_client = boto3.client("lambda", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)

    # 2. Criar o Payload (Simulando o que o API Gateway enviaria)
    payload = {
        "body": json.dumps({
            "candidate_name": "Tester Silva",
            "question_id": "Q1-Intro"
        })
    }

    try:
        # 3. Invocar a Lambda
        print("📡 Chamando a Lambda na AWS...")
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # 4. Ler a Resposta
        response_payload = json.loads(response['Payload'].read())
        
        # Verifica se a Lambda rodou mas deu erro interno (ex: 500)
        if "errorMessage" in response_payload:
            print(f"❌ Erro na execução da Lambda: {response_payload['errorMessage']}")
            return

        status_code = response_payload.get("statusCode")
        body = json.loads(response_payload.get("body", "{}"))

        if status_code == 201:
            print("\n✅ SUCESSO! A Lambda respondeu corretamente.")
            print(f"   -> Session ID: {body['session_id']}")
            print(f"   -> Upload URL gerada: {body['upload_url'][:50]}... (truncada)")
            
            # 5. Validação Extra: Verificar se salvou no DynamoDB
            verify_dynamodb(dynamodb, body['session_id'])
        else:
            print(f"\n⚠️ Falha: Status Code {status_code}")
            print(f"   Detalhes: {body}")

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"\n❌ Erro: Não encontrei a função '{FUNCTION_NAME}'.")
        print("   Verifique se o nome no arquivo Python bate com o output do Terraform.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")

def verify_dynamodb(dynamodb_resource, session_id):
    # Tenta achar a tabela pelo padrão de nome
    table_name = "mock-interview-sessions-dev"
    table = dynamodb_resource.Table(table_name)
    
    print(f"\n🔍 Verificando persistência no DynamoDB ({table_name})...")
    response = table.get_item(Key={'session_id': session_id})
    
    if 'Item' in response:
        item = response['Item']
        print("✅ ITEM ENCONTRADO NO BANCO!")
        print(f"   -> Status: {item.get('status')}")
        print(f"   -> Candidato: {item.get('candidate_name')}")
        print("   -> Expira em: Sim (TTL Configurado)")
    else:
        print("❌ ERRO: O item não foi encontrado no DynamoDB.")

if __name__ == "__main__":
    run_test()