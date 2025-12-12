import asyncio
import os
import math
import struct
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ ERRO: GEMINI_API_KEY não encontrada.")
    exit(1)

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
MODEL_ID = "gemini-2.5-flash-native-audio-preview-09-2025"

def generate_beep_pcm(duration_sec=1.0, sample_rate=16000, freq=440.0):
    """Gera 1.0s de áudio PCM puro (Bip)."""
    print(f"Gerando {duration_sec}s de audio ({freq}Hz)...")
    num_samples = int(duration_sec * sample_rate)
    pcm_data = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        sample = int(32767.0 * math.sin(2 * math.pi * freq * t))
        pcm_data.extend(struct.pack('<h', sample))
    return pcm_data

async def send_audio_stream(session):
    pcm_data = generate_beep_pcm()
    chunk_size = 4096 
    
    # 1. Avisa que vai mandar
    print("Enviando aviso de texto...")
    await session.send(input="I am sending audio now. Listen closely.", end_of_turn=True)
    await asyncio.sleep(1)
    
    # 2. Envia o Áudio (Método Robusto)
    print("Enviando stream de audio...")
    for i in range(0, len(pcm_data), chunk_size):
        chunk = pcm_data[i:i+chunk_size]
        
        # Usamos session.send com input dict - isso NÃO crasha
        await session.send(input={
            "mime_type": "audio/pcm;rate=16000",
            "data": chunk
        })
        await asyncio.sleep(0.01)
        
    print("Audio enviado.")
    
    # 3. [TRUQUE] Pergunta de confirmação para forçar o processamento do buffer
    print("Perguntando se ouviu...")
    await session.send(input="Did you hear the beep sound just now? Yes or No?", end_of_turn=True)

async def receive_responses(session):
    print("Escutando...")
    async for response in session.receive():
        server_content = response.server_content
        if server_content and server_content.model_turn:
            for part in server_content.model_turn.parts:
                if part.text: 
                    print(f"IA: {part.text}")
                if part.inline_data: 
                    print(f"IA enviou audio ({len(part.inline_data.data)} bytes)!")
                    return # Sucesso!
        
        if server_content and server_content.turn_complete:
            print("🏁 Turno finalizado.")

async def run_test():
    config = {
        "response_modalities": ["AUDIO"], # Força resposta em áudio
        "speech_config": {
            "voice_config": {"prebuilt_voice_config": {"voice_name": "Aoede"}}
        }
    }
    
    async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
        sender = asyncio.create_task(send_audio_stream(session))
        receiver = asyncio.create_task(receive_responses(session))
        
        # Espera até receber áudio ou timeout
        done, pending = await asyncio.wait([sender, receiver], timeout=15, return_when=asyncio.FIRST_COMPLETED)
        for task in pending: task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"Erro: {e}")