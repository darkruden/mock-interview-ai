import { useState, useRef, useEffect } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';

// Configuração do WebSocket do Gemini
const MODEL = "models/gemini-2.0-flash-exp"; // Usando o modelo experimental mais rápido
const BASE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent";

export function useGeminiLive(apiBaseUrl) {
    const [status, setStatus] = useState('disconnected'); // disconnected, connecting, connected, error
    const [isSpeaking, setIsSpeaking] = useState(false); // Se a IA está falando
    const websocketRef = useRef(null);
    const audioContextRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const processorRef = useRef(null);

    // Pega o token efêmero da nossa API
    const getEphemeralToken = async () => {
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken?.toString();

        const response = await fetch(`${apiBaseUrl}/auth/gemini-token`, {
            headers: { Authorization: idToken }
        });
        const data = await response.json();
        return data.token;
    };

    const connect = async () => {
        try {
            setStatus('connecting');
            const token = await getEphemeralToken();

            // Monta URL com o token direto (seguro pois o token expira em 10min)
            const wsUrl = `${BASE_URL}?key=${token}`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("WebSocket Conectado!");
                setStatus('connected');
                // Envia configuração inicial (Setup)
                ws.send(JSON.stringify({
                    setup: {
                        model: MODEL,
                        generationConfig: {
                            responseModalities: ["AUDIO"]
                        }
                    }
                }));
                startMicrophone(ws);
            };

            ws.onmessage = async (event) => {
                const data = await event.data.text(); // O Gemini manda Blob/Text misturado
                let response;
                try {
                    response = JSON.parse(data);
                } catch (e) { return; }

                // Se receber áudio da IA, toca
                if (response.serverContent?.modelTurn?.parts?.[0]?.inlineData) {
                    const audioData = response.serverContent.modelTurn.parts[0].inlineData.data;
                    playAudioChunk(audioData);
                }
            };

            ws.onclose = () => {
                console.log(`WebSocket Fechado. Código: ${event.code}, Motivo: ${event.reason}`);

                stopAudio();
                setStatus('disconnected');
            };

            ws.onerror = (err) => {
                console.error("Erro WS:", err);
                setStatus('error');
            };

            websocketRef.current = ws;

        } catch (err) {
            console.error(err);
            setStatus('error');
        }
    };

    const disconnect = () => {
        if (websocketRef.current) websocketRef.current.close();
        stopAudio();
        setStatus('disconnected');
    };

    // --- Lógica de Áudio (Microfone -> PCM 16kHz -> WebSocket) ---
    const startMicrophone = async (ws) => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
            mediaStreamRef.current = stream;
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

            const source = audioContextRef.current.createMediaStreamSource(stream);

            // Processador simples para pegar o buffer cru (Worklet seria ideal, mas ScriptProcessor é mais fácil de implementar num arquivo só)
            const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
            processor.onaudioprocess = (e) => {
                if (ws.readyState !== WebSocket.OPEN) return;

                const inputData = e.inputBuffer.getChannelData(0);
                // Converte Float32 para Int16 (PCM)
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
                }

                // Converte para Base64 e envia
                const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));

                ws.send(JSON.stringify({
                    realtimeInput: {
                        mediaChunks: [{
                            mimeType: "audio/pcm; rate=16000",
                            data: base64Audio
                        }]
                    }
                }));
            };

            source.connect(processor);
            processor.connect(audioContextRef.current.destination); // Necessário para o ScriptProcessor rodar
            processorRef.current = processor;

        } catch (e) {
            console.error("Erro no Mic:", e);
        }
    };

    const stopAudio = () => {
        if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach(track => track.stop());
        if (processorRef.current) processorRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
    };

    // --- Lógica de Playback (PCM Base64 -> Falante) ---
    const playAudioChunk = async (base64Data) => {
        try {
            setIsSpeaking(true);
            const binaryString = atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);

            const int16Data = new Int16Array(bytes.buffer);
            const float32Data = new Float32Array(int16Data.length);
            for (let i = 0; i < int16Data.length; i++) {
                float32Data[i] = int16Data[i] / 0x7FFF;
            }

            // Toca o buffer
            if (!audioContextRef.current) audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 }); // Gemini 2 costuma devolver 24k

            const buffer = audioContextRef.current.createBuffer(1, float32Data.length, 24000);
            buffer.getChannelData(0).set(float32Data);

            const source = audioContextRef.current.createBufferSource();
            source.buffer = buffer;
            source.connect(audioContextRef.current.destination);
            source.onended = () => setIsSpeaking(false);
            source.start();

        } catch (e) {
            console.error("Erro playback:", e);
        }
    };

    return { status, isSpeaking, connect, disconnect };
}