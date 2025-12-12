import asyncio
import websockets
import json
import os
import sys
import socket
import ssl
import logging

# --- CONFIGURAÇÃO DE LOGS (Verboso) ---
# Isso vai mostrar o header HTTP exato e o handshake SSL
logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)  # Ativa logs detalhados da lib websockets
logger.addHandler(logging.StreamHandler())

# Tenta carregar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONSTANTES ---
HOST = "generativelanguage.googleapis.com"
MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025" # Modelo atualizado
API_KEY = os.getenv("GEMINI_API_KEY")

def check_dns_and_tcp():
    """Etapa 1: Verifica se a internet consegue chegar no Google."""
    print(f"\n[1/3] 🔍 Testando conectividade básica com {HOST}...")
    
    # 1. DNS
    try:
        ip = socket.gethostbyname(HOST)
        print(f"   ✅ DNS Resolvido: {ip}")
    except socket.gaierror:
        print("   ❌ ERRO CRÍTICO: Não foi possível resolver o DNS. Verifique sua internet.")
        return False

    # 2. TCP Handshake (Porta 443)
    try:
        sock = socket.create_connection((HOST, 443), timeout=5)
        print("   ✅ Conexão TCP (Porta 443) estabelecida.")
        sock.close()
    except Exception as e:
        print(f"   ❌ ERRO CRÍTICO: Falha ao conectar na porta 443. Firewall? Erro: {e}")
        return False
        
    return True

async def test_websocket_handshake():
    """Etapa 2: Tenta o WebSocket com logs detalhados."""
    print(f"\n[2/3] 🔌 Iniciando Handshake WebSocket...")
    
    if not API_KEY:
        print("   ❌ ERRO: GEMINI_API_KEY não encontrada.")
        return

    # URL Construída
    url = f"wss://{HOST}/v1alpha/{MODEL}:BidiGenerateContent?key={API_KEY}"
    print(f"   ℹ️ URL Alvo: wss://{HOST}/v1alpha/{MODEL}:BidiGenerateContent?key=HIDDEN")

    try:
        # Aumentamos o timeout para 20s para descartar latência
        async with websockets.connect(
            url, 
            open_timeout=20, 
            ping_timeout=20,
            close_timeout=10
        ) as ws:
            print("\n[3/3] 🎉 Conexão WebSocket ABERTA! O servidor aceitou a conexão.")
            
            # Tenta enviar o Setup
            setup_msg = {
                "setup": {
                    "model": MODEL,
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Aoede" } }
                        }
                    }
                }
            }
            
            print("   📤 Enviando payload de Setup...")
            await ws.send(json.dumps(setup_msg))
            
            print("   ⏳ Aguardando confirmação do servidor...")
            response = await ws.recv()
            print(f"   📥 Resposta do Servidor: {response}")
            
    except asyncio.TimeoutError:
        print("\n❌ ERRO: Timeout. O servidor não respondeu ao Handshake em 20 segundos.")
        print("   DICA: Isso geralmente indica que o modelo está incorreto ou a URL mudou.")
        
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n❌ ERRO HTTP {e.status_code}: O servidor rejeitou a conexão.")
        print(f"   Headers de resposta: {e.headers}")
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    print("="*60)
    print("🛠️  DIAGNÓSTICO AVANÇADO DE CONEXÃO GEMINI LIVE")
    print("="*60)
    
    if check_dns_and_tcp():
        try:
            asyncio.run(test_websocket_handshake())
        except KeyboardInterrupt:
            print("\nCancelado pelo usuário.")