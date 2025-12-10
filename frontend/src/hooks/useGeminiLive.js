import { useState, useRef, useEffect } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';

// Configuração do WebSocket do Gemini
const MODEL = "models/gemini-2.5-flash";
const BASE_URL = "wss://generativelanguage.googleapis.com/v1alpha/models/gemini-2.5-flash:BidiGenerateContent";

export function useGeminiLive(apiBaseUrl) {
    const [status, setStatus] = useState('disconnected');
    const [isSpeaking, setIsSpeaking] = useState(false);
    const websocketRef = useRef(null);
    const audioContextRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const processorRef = useRef(null);

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

            let rawToken = await getEphemeralToken();
            console.log("🔍 TOKEN RECEBIDO DA AWS:", rawToken);
            const cleanToken = rawToken.includes('/') ? rawToken.split('/').pop() : rawToken;
            console.log("✨ TOKEN LIMPO PARA O GOOGLE:", cleanToken);
            const wsUrl = `${BASE_URL}?access_token=${cleanToken}`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log("WebSocket Conectado!");
                setStatus('connected');

                // Configuração inicial (Setup)
                ws.send(JSON.stringify({
                    setup: {
                        model: MODEL,
                        generationConfig: {
                            responseModalities: ["AUDIO"],
                            speechConfig: {
                                voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } }
                            }
                        }
                    }
                }));
                startMicrophone(ws);
            };

            ws.onmessage = async (event) => {
                let response;
                try {
                    // [CORREÇÃO] Verifica se é Blob (Binário) ou Texto Puro
                    let textData;
                    if (event.data instanceof Blob) {
                        textData = await event.data.text();
                    } else {
                        textData = event.data;
                    }

                    response = JSON.parse(textData);
                } catch (e) {
                    console.error("Erro ao parsear mensagem:", e);
                    return;
                }

                // Se receber áudio da IA, toca
                if (response.serverContent?.modelTurn?.parts?.[0]?.inlineData) {
                    const audioData = response.serverContent.modelTurn.parts[0].inlineData.data;
                    playAudioChunk(audioData);
                }

                // Log de fim de turno (debug)
                if (response.serverContent?.turnComplete) {
                    console.log("IA terminou de falar.");
                }
            };

            // [CORREÇÃO] Adicionado 'event' aqui para não dar erro no log
            ws.onclose = (event) => {
                console.log(`WebSocket Fechado. Código: ${event.code}, Motivo: ${event.reason}`);

                // Códigos de erro comuns: 
                // 4000-4999: Erro de Protocolo (Modelo errado, JSON inválido)
                // 1006: Erro de Rede (CORS, Queda de net)

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

    // --- Lógica de Áudio (Mantida igual) ---
    const startMicrophone = async (ws) => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
            mediaStreamRef.current = stream;
            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });

            const source = audioContextRef.current.createMediaStreamSource(stream);
            const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);

            processor.onaudioprocess = (e) => {
                if (ws.readyState !== WebSocket.OPEN) return;

                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
                }
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
            processor.connect(audioContextRef.current.destination);
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

            if (!audioContextRef.current) audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });

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