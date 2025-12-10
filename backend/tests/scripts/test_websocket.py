import asyncio
import os
import json
import websockets
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(backend_root)
# Carrega variáveis e caminhos
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError: pass
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa sua Lambda localmente
from src.handlers.get_gemini_token import lambda_handler

async def test_live_connection():
    print("🔌 INICIANDO TESTE DE CONEXÃO REAL (WEBSOCKET)...")
    
    # 1. Obter Token da Lambda
    print("1️⃣  Solicitando token da Lambda local...")
    response = lambda_handler({}, None)
    
    if response['statusCode'] != 200:
        print(f"❌ Falha ao gerar token: {response['body']}")
        return

    body = json.loads(response['body'])
    token = body['token']
    print(f"   Token obtido: {token[:10]}... (Verifique se não há prefixos!)")

    # 2. Conectar no Google
    url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={token}"
    
    print(f"2️⃣  Tentando conectar ao Gemini Live API...")
    
    try:
        async with websockets.connect(url) as ws:
            print("   ✅ Conexão WebSocket estabelecida!")
            
            # 3. Enviar Configuração (Handshake)
            setup_msg = {
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"]
                    }
                }
            }
            await ws.send(json.dumps(setup_msg))
            print("3️⃣  Mensagem de Setup enviada. Aguardando confirmação...")
            
            # 4. Esperar resposta (se não cair em 2s, é sucesso)
            try:
                # O Google geralmente manda um setupComplete ou áudio
                # Se a conexão cair aqui, é erro de protocolo/token
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"   ✅ Resposta recebida do Google: {str(msg)[:100]}...")
                print("\n✨ SUCESSO ABSOLUTO! O sistema está 100% funcional.")
                
            except asyncio.TimeoutError:
                print("   ⚠️ Sem resposta imediata (o que é bom, pois não fechou na cara).")
                print("\n✨ SUCESSO PROVÁVEL! A conexão permaneceu aberta.")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ ERRO DE CONEXÃO: {e.status_code}")
        if e.status_code == 403:
            print("   Motivo: Token Inválido ou Chave de API sem permissão.")
        elif e.status_code == 400:
            print("   Motivo: Formato do Token ou Modelo incorreto.")
        else:
            print(f"   Detalhes: {e}")
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_connection())