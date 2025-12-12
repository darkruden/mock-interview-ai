import { useState, useRef } from 'react';
import { fetchAuthSession } from 'aws-amplify/auth';
import { GoogleGenAI } from '@google/genai';

const MODEL_ID = "gemini-2.5-flash-native-audio-preview-09-2025";

export function useGeminiLive(apiBaseUrl) {
    const [status, setStatus] = useState('disconnected');
    const [isSpeaking, setIsSpeaking] = useState(false);

    const sessionRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const audioInputContextRef = useRef(null);
    const audioOutputContextRef = useRef(null);
    const processorRef = useRef(null);
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);

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
            const apiKey = await getEphemeralToken();
            console.log("🔑 Chave obtida.");

            const client = new GoogleGenAI({ apiKey: apiKey });

            const session = await client.live.connect({
                model: MODEL_ID,
                config: {
                    responseModalities: ["AUDIO"],
                    speechConfig: {
                        voiceConfig: { prebuiltVoiceConfig: { voiceName: "Aoede" } }
                    }
                },
                callbacks: {
                    onopen: () => {
                        console.log("✅ Conexão Live Estabelecida!");
                        setStatus('connected');
                    },
                    onmessage: (msg) => {
                        // Áudio
                        if (msg.serverContent?.modelTurn?.parts?.[0]?.inlineData) {
                            // console.log("🎵 Áudio recebido!");
                            const audioData = msg.serverContent.modelTurn.parts[0].inlineData.data;
                            enqueueAudioChunk(audioData);
                        }
                        // Texto/Logs
                        if (msg.serverContent?.modelTurn?.parts?.[0]?.text) {
                            console.log("📝 IA:", msg.serverContent.modelTurn.parts[0].text);
                        }
                    },
                    onclose: (e) => {
                        console.log("🔌 Conexão fechada:", e);
                        cleanup();
                        setStatus('disconnected');
                    },
                    onerror: (err) => {
                        console.error("❌ Erro na sessão:", err);
                        setStatus('error');
                    }
                }
            });

            sessionRef.current = session;

            // Inicia Microfone com Downsampling
            await startMicrophone(session);

        } catch (err) {
            console.error("Erro fatal ao conectar:", err);
            setStatus('error');
            cleanup();
        }
    };

    const disconnect = () => {
        console.log("Desconectando...");
        cleanup();
        setStatus('disconnected');
    };

    const cleanup = () => {
        stopAudioInput();
        sessionRef.current = null;
        audioQueueRef.current = [];
        isPlayingRef.current = false;
    };

    // --- ALGORITMO DE DOWNSAMPLING (O Segredo) ---
    const downsampleTo16k = (buffer, inputRate) => {
        if (inputRate === 16000) return buffer;

        const compression = inputRate / 16000;
        const length = Math.floor(buffer.length / compression);
        const result = new Float32Array(length);

        for (let i = 0; i < length; i++) {
            // Pega o sample correspondente (interpolação simples)
            // Multiplicamos por 4.0 para AUMENTAR O GANHO (Volume Boost)
            // Isso resolve o problema de "IA não me ouve"
            let sample = buffer[Math.floor(i * compression)] * 4.0;

            // Clampa o valor entre -1 e 1 para não distorcer
            result[i] = Math.max(-1, Math.min(1, sample));
        }
        return result;
    };

    // --- AUDIO INPUT ---
    const startMicrophone = async (session) => {
        try {
            console.log("🎙️ Iniciando microfone...");
            // Pedimos a configuração padrão do navegador (geralmente 44.1k ou 48k)
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            mediaStreamRef.current = stream;

            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            audioInputContextRef.current = new AudioContextClass();
            const sourceSampleRate = audioInputContextRef.current.sampleRate;
            console.log(`🎙️ Input Nativo: ${sourceSampleRate}Hz -> Convertendo para 16000Hz`);

            if (audioInputContextRef.current.state === 'suspended') {
                await audioInputContextRef.current.resume();
            }

            const source = audioInputContextRef.current.createMediaStreamSource(stream);
            // Buffer maior (4096) para processar melhor o downsampling
            const processor = audioInputContextRef.current.createScriptProcessor(4096, 1, 1);

            let chunksSent = 0;

            processor.onaudioprocess = (e) => {
                if (!sessionRef.current) return;

                const inputData = e.inputBuffer.getChannelData(0);

                // 1. Converte 48k/44k -> 16k e aplica Boost de Volume
                const downsampledData = downsampleTo16k(inputData, sourceSampleRate);

                // 2. Converte Float32 -> Int16 PCM
                const pcmData = new Int16Array(downsampledData.length);
                for (let i = 0; i < downsampledData.length; i++) {
                    const s = downsampledData[i];
                    pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }

                const base64Audio = arrayBufferToBase64(pcmData.buffer);

                try {
                    // Agora enviamos SEMPRE como 16000, pois convertemos manualmente
                    sessionRef.current.sendRealtimeInput([{
                        mimeType: "audio/pcm;rate=16000",
                        data: base64Audio
                    }]);

                    chunksSent++;
                    if (chunksSent % 50 === 0) console.log(`🎤 Enviando (16k Convertido)...`);

                } catch (err) {
                    // Ignora erros de socket fechado
                }
            };

            source.connect(processor);
            processor.connect(audioInputContextRef.current.destination);
            processorRef.current = processor;
            console.log("🎙️ Microfone ativo!");

        } catch (e) {
            console.error("Erro no Microfone:", e);
            cleanup();
        }
    };

    const stopAudioInput = () => {
        if (mediaStreamRef.current) mediaStreamRef.current.getTracks().forEach(t => t.stop());
        if (processorRef.current) processorRef.current.disconnect();
        if (audioInputContextRef.current) audioInputContextRef.current.close();
    };

    function arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    // --- AUDIO OUTPUT ---
    const enqueueAudioChunk = (base64Data) => {
        audioQueueRef.current.push(base64Data);
        if (!isPlayingRef.current) playNextChunk();
    };

    const playNextChunk = async () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            setIsSpeaking(false);
            return;
        }

        isPlayingRef.current = true;
        setIsSpeaking(true);
        const base64Data = audioQueueRef.current.shift();

        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!audioOutputContextRef.current) {
                // Gemini devolve 24kHz
                audioOutputContextRef.current = new AudioContextClass({ sampleRate: 24000 });
            }

            if (audioOutputContextRef.current.state === 'suspended') {
                await audioOutputContextRef.current.resume();
            }

            const binaryString = atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) bytes[i] = binaryString.charCodeAt(i);
            const int16Data = new Int16Array(bytes.buffer);
            const float32Data = new Float32Array(int16Data.length);
            for (let i = 0; i < int16Data.length; i++) {
                float32Data[i] = int16Data[i] / 32768.0;
            }

            const buffer = audioOutputContextRef.current.createBuffer(1, float32Data.length, 24000);
            buffer.getChannelData(0).set(float32Data);

            const source = audioOutputContextRef.current.createBufferSource();
            source.buffer = buffer;
            source.connect(audioOutputContextRef.current.destination);
            source.onended = () => playNextChunk();
            source.start();
            console.log("🔊 Tocando...");

        } catch (e) {
            console.error("Erro playback:", e);
            playNextChunk();
        }
    };

    return { status, isSpeaking, connect, disconnect };
}