import json
import os
import boto3
from google import genai
from google.genai import types

# Configuração AWS
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("SESSIONS_TABLE", "MockInterviewSessions")
AUDIO_BUCKET = os.environ.get("AUDIO_BUCKET_NAME", "mock-interview-audio-bucket")

def handler(event, context):
    """
    Processa o áudio de entrevista usando Gemini 2.5 Flash (Versão Estável).
    Entrada: Evento JSON com { session_id, file_key }
    Saída: JSON Estruturado { transcription, feedback, score, follow_up_question }
    """
    print(f"🚀 Event received: {json.dumps(event)}")
    
    try:
        # 1. Validação da Entrada
        body = json.loads(event.get("body", "{}"))
        session_id = body.get("session_id")
        file_key = body.get("file_key")
        
        if not session_id or not file_key:
            return {
                "statusCode": 400, 
                "body": json.dumps({"error": "Missing session_id or file_key"})
            }

        # 2. Setup do Gemini Client (Nova SDK google-genai)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {
                "statusCode": 500, 
                "body": json.dumps({"error": "GEMINI_API_KEY not configured in Lambda"})
            }
        
        client = genai.Client(api_key=api_key)

        # 3. Baixar Áudio do S3 para Processamento Local (/tmp)
        # Nota: Lambda tem armazenamento temporário efêmero em /tmp
        download_path = f"/tmp/{os.path.basename(file_key)}"
        print(f"⬇️ Downloading from {AUDIO_BUCKET}/{file_key} to {download_path}...")
        
        s3.download_file(AUDIO_BUCKET, file_key, download_path)
        
        # 4. Carregar bytes do áudio
        with open(download_path, "rb") as f:
            audio_bytes = f.read()

        # 5. Definição do Prompt de Engenharia de Software
        # Focamos em JSON estrito e persona sênior.
        system_instruction = """
        Você é um Arquiteto de Software Sênior conduzindo uma entrevista técnica.
        Analise o áudio da resposta do candidato.
        
        Se o áudio for inaudível ou silêncio, retorne score 0 e feedback "Áudio não detectado".
        
        Sua resposta DEVE ser estritamente um objeto JSON com esta estrutura:
        {
            "transcription": "Texto exato do que o candidato falou",
            "feedback": "Análise crítica técnica (pontos positivos e melhorias)",
            "score": Inteiro de 0 a 100,
            "follow_up_question": "Uma pergunta técnica desafiadora baseada no que foi dito"
        }
        """

        print("🤖 Invoking Gemini 2.5 Flash...")

        # 6. Chamada ao Modelo (Gemini 2.5 Flash Estável)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3"),
                        types.Part.from_text(text=system_instruction)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", # Garante JSON puro (sem markdown)
                temperature=0.5 # Menor temperatura para avaliação mais objetiva
            )
        )

        # 7. Parsing e Tratamento de Resposta
        print(f"✅ Gemini Raw Response: {response.text}")
        
        try:
            ai_data = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback de segurança (raro com response_mime_type)
            print("⚠️ JSON parsing failed, returning raw error")
            raise ValueError("Failed to parse AI response as JSON")

        # 8. Atualizar Persistência (DynamoDB)
        table = dynamodb.Table(TABLE_NAME)
        table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET transcription = :t, feedback = :f, score = :s, follow_up = :q, last_updated = :u, status = :st",
            ExpressionAttributeValues={
                ":t": ai_data.get("transcription", ""),
                ":f": ai_data.get("feedback", ""),
                ":s": ai_data.get("score", 0),
                ":q": ai_data.get("follow_up_question", ""),
                ":u": str(context.aws_request_id), # Usando ID da request como timestamp simples ou use datetime
                ":st": "COMPLETED"
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
            "body": json.dumps(ai_data)
        }

    except Exception as e:
        print(f"❌ Critical Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }