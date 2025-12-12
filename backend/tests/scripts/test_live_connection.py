import asyncio
import websockets
import json
import os
import sys

# Tenta carregar variáveis de ambiente se não estiverem setadas
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

async def test_gemini_connection():
    """
    Simula o comportamento do Frontend:
    1. Obtém a API Key (neste teste, pegamos da env var local para isolar)
    2. Conecta no WebSocket do Google
    3. Envia mensagem de configuração (Setup)
    4. Mantém a conexão aberta por alguns segundos
    """
    
    print("🔍 [DIAGNÓSTICO] Iniciando teste de conexão WebSocket...")

    # 1. Validação da Chave
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERRO: Variável GEMINI_API_KEY não encontrada.")
        print("   -> Configure no seu .env ou exporte no terminal.")
        return

    print(f"🔑 Chave detectada: {api_key[:5]}...{api_key[-5:]}")

    # 2. Definição da URL (A mesma do seu frontend)
    host = "generativelanguage.googleapis.com"
    model = "models/gemini-2.5-flash-native-audio-preview-09-2025"
    url = f"wss://{host}/v1alpha/{model}:BidiGenerateContent?key={api_key}"

    print(f"🌐 Tentando conectar em: {url.split('?')[0]}...")

    try:
        async with websockets.connect(url) as ws:
            print("✅ Conexão WebSocket estabelecida com sucesso!")
            
            # 3. Envio do Setup (Cópia exata do seu frontend)
            setup_msg = {
                "setup": {
                    "model": model,
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": { 
                                "prebuiltVoiceConfig": { "voiceName": "Aoede" } 
                            }
                        }
                    }
                }
            }
            
            print("📤 Enviando mensagem de Setup...")
            await ws.send(json.dumps(setup_msg))
            
            # 4. Aguardar Confirmação (Handshake da Aplicação)
            print("⏳ Aguardando resposta do servidor...")
            
            # O servidor geralmente responde com "setupComplete" ou apenas abre o canal
            try:
                # Espera até 5 segundos por uma resposta
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"📥 Resposta recebida: {response}")
                print("🎉 SUCESSO! A conexão é estável e a chave é válida.")
                
            except asyncio.TimeoutError:
                print("⚠️ Aviso: Nenhuma resposta de setup recebida em 5s (isso pode ser normal se o modelo estiver apenas escutando).")
                print("🎉 SUCESSO: A conexão não caiu imediatamente.")

            # Mantém aberto mais um pouco para simular silêncio
            await asyncio.sleep(1)
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ ERRO DE PROTOCOLO (HTTP {e.status_code}):")
        if e.status_code == 400:
            print("   -> Provavelmente Payload de Setup inválido ou Modelo incorreto.")
        elif e.status_code == 403:
            print("   -> Chave de API inválida ou sem permissão para este modelo.")
        elif e.status_code == 404:
            print("   -> URL do WebSocket incorreta.")
        else:
            print(f"   -> Detalhes: {e}")

    except Exception as e:
        print(f"❌ ERRO GERAL: {str(e)}")

if __name__ == "__main__":
    # Verifica dependência
    try:
        import websockets
    except ImportError:
        print("Instalando dependência 'websockets'...")
        os.system(f"{sys.executable} -m pip install websockets python-dotenv")
        print("-" * 30)

    try:
        asyncio.run(test_gemini_connection())
    except KeyboardInterrupt:
        print("\nTeste interrompido pelo usuário.")