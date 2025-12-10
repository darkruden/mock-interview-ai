import asyncio
import os
import json
import websockets
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(backend_root)
# Setup de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError: pass
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.handlers.get_gemini_token import lambda_handler

async def try_connect(name, url, headers=None):
    print(f"\n🔄 TESTE: {name}")
    print(f"   URL: {url[:60]}...")
    if headers: print(f"   Headers: {headers}")
    
    try:
        async with websockets.connect(url, additional_headers=headers) as ws:
            print(f"   ✅ CONEXÃO ACEITA! ({name} funcionou)")
            
            # Tenta handshake para garantir
            await ws.send(json.dumps({
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generationConfig": {"responseModalities": ["AUDIO"]}
                }
            }))
            return True
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"   ❌ FALHOU: Status {e.status_code}")
        # Se for 1007/400/403, mostra o erro
        return False
    except Exception as e:
        print(f"   ❌ ERRO: {str(e)}")
        return False

async def run_diagnostics():
    print("🕵️‍♂️ DIAGNÓSTICO DE AUTENTICAÇÃO GEMINI LIVE")
    
    # 1. Pega o token limpo
    resp = lambda_handler({}, None)
    token = json.loads(resp['body'])['token']
    print(f"🔑 Token obtido: {token[:10]}...")
    
    base_url = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"

    # --- CENÁRIO 1: Padrão (que estava falhando) ---
    # Tenta usar ?key=
    success = await try_connect(
        "Modo KEY (?key=...)", 
        f"{base_url}?key={token}"
    )
    
    # --- CENÁRIO 2: Modo Access Token (Comum em OAuth) ---
    # Tenta usar ?access_token=
    if not success:
        success = await try_connect(
            "Modo ACCESS_TOKEN (?access_token=...)", 
            f"{base_url}?access_token={token}"
        )

    # --- CENÁRIO 3: Modo Header (Bearer Token) ---
    # Se funcionar aqui, o token é válido, mas o navegador tem limitações
    if not success:
        success = await try_connect(
            "Modo HEADER (Authorization: Bearer ...)", 
            base_url,
            headers={"Authorization": f"Bearer {token}"}
        )
    
    # --- CENÁRIO 4: Modo Header (x-goog-api-key) ---
    if not success:
        success = await try_connect(
            "Modo HEADER (x-goog-api-key)", 
            base_url,
            headers={"x-goog-api-key": token}
        )

if __name__ == "__main__":
    asyncio.run(run_diagnostics())