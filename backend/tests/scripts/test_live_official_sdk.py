import asyncio
import os
from google import genai
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERRO: GEMINI_API_KEY não encontrada.")
    exit(1)

# Cliente oficial (v1.0+)
client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})

# O modelo correto para Live API segundo a documentação mais recente
MODEL_ID = "gemini-2.0-flash-exp"

async def test_official_connection():
    print(f"Testando conexao via SDK Oficial com o modelo: {MODEL_ID}")
    
    config = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {"prebuilt_voice_config": {"voice_name": "Aoede"}}
        }
    }

    try:
        # Tenta conectar usando a abstração da SDK
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print("SUCESSO! Conexao estabelecida com a SDK Oficial.")
            
            # Envia um "Olá" simples em texto para ver se responde
            print("Enviando mensagem de teste...")
            await session.send_client_content(
                turns={"role": "user", "parts": [{"text": "Hello, are you there?"}]}, 
                turn_complete=True
            )
            
            print("Aguardando audio de resposta...")
            async for response in session.receive():
                if response.server_content:
                    print("Recebido chunk do servidor!")
                    # Se recebermos qualquer coisa, o teste passou
                    break
            
            print("Teste concluido com sucesso total.")

    except Exception as e:
        print(f"\nFALHA na conexao via SDK: {e}")
        # Dica de debug baseada no erro
        if "404" in str(e):
            print("   -> Dica: O modelo pode não estar disponível ou o nome está errado.")
        elif "403" in str(e):
            print("   -> Dica: Chave de API sem permissão ou inválida.")

if __name__ == "__main__":
    asyncio.run(test_official_connection())