import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useGeminiLive } from './useGeminiLive';

// --- MOCKS ---

// 1. Instância do AudioContext (o objeto com os métodos)
const mockAudioContextInstance = {
    createMediaStreamSource: vi.fn(() => ({ connect: vi.fn() })),
    createScriptProcessor: vi.fn(() => ({
        connect: vi.fn(),
        disconnect: vi.fn(),
        onaudioprocess: null
    })),
    destination: {},
    close: vi.fn(),
    createBuffer: vi.fn(() => ({ getChannelData: vi.fn(() => new Float32Array(0)) })),
    createBufferSource: vi.fn(() => ({
        buffer: null,
        connect: vi.fn(),
        start: vi.fn(),
        onended: null
    })),
};

// 2. Classe Mock para o Construtor (Para funcionar com 'new')
class MockAudioContext {
    constructor() {
        return mockAudioContextInstance;
    }
}

// 3. Mock do WebSocket
class MockWebSocket {
    constructor(url) {
        this.url = url;
        this.readyState = 0;
        this.send = vi.fn();
        this.close = vi.fn();

        setTimeout(() => {
            this.readyState = 1;
            if (this.onopen) this.onopen();
        }, 50);
    }
}

// 4. Mock do MediaStream
const mockMediaStream = {
    getTracks: () => [{ stop: vi.fn() }]
};

describe('useGeminiLive Hook', () => {

    beforeEach(() => {
        // --- INJEÇÃO NO AMBIENTE GLOBAL ---

        global.fetch = vi.fn(() =>
            Promise.resolve({
                json: () => Promise.resolve({ token: 'fake-gemini-token' }),
            })
        );

        global.WebSocket = MockWebSocket;

        // [CORREÇÃO] Injetamos uma classe real envolta em um Spy
        // Isso garante que 'new AudioContext()' não lance erro
        global.window.AudioContext = vi.fn(MockAudioContext);
        global.window.webkitAudioContext = vi.fn(MockAudioContext);

        Object.defineProperty(global.navigator, 'mediaDevices', {
            value: {
                getUserMedia: vi.fn().mockResolvedValue(mockMediaStream),
            },
            writable: true,
        });

        vi.mock('aws-amplify/auth', () => ({
            fetchAuthSession: vi.fn().mockResolvedValue({
                tokens: { idToken: { toString: () => 'fake-aws-token' } }
            })
        }));
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('deve iniciar com status "disconnected"', () => {
        const { result } = renderHook(() => useGeminiLive('http://api-fake.com'));
        expect(result.current.status).toBe('disconnected');
        expect(result.current.isSpeaking).toBe(false);
    });

    it('deve mudar status para "connecting" e depois "connected" ao chamar connect()', async () => {
        const { result } = renderHook(() => useGeminiLive('http://api-fake.com'));

        await act(async () => {
            await result.current.connect();
        });

        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/auth/gemini-token'),
            expect.anything()
        );

        await waitFor(() => {
            expect(result.current.status).toBe('connected');
        });
    });

    it('deve limpar recursos e mudar status para "disconnected" ao chamar disconnect()', async () => {
        const { result } = renderHook(() => useGeminiLive('http://api-fake.com'));

        // 1. Conectar
        await act(async () => {
            await result.current.connect();
        });

        // 2. Aguarda conexão
        await waitFor(() => expect(result.current.status).toBe('connected'));

        // 3. Aguarda a criação do AudioContext (Garante que startMicrophone terminou com sucesso)
        await waitFor(() => {
            expect(global.window.AudioContext).toHaveBeenCalled();
        }, { timeout: 2000 });

        // 4. Desconectar
        act(() => {
            result.current.disconnect();
        });

        // 5. Assertivas
        expect(result.current.status).toBe('disconnected');
        // Agora vai passar porque o objeto foi criado corretamente sem erro no construtor
        expect(mockAudioContextInstance.close).toHaveBeenCalled();
    });

    it('deve ir para estado de "error" se a API de token falhar', async () => {
        global.fetch.mockRejectedValueOnce(new Error('API Offline'));

        const { result } = renderHook(() => useGeminiLive('http://api-fake.com'));

        await act(async () => {
            await result.current.connect();
        });

        expect(result.current.status).toBe('error');
    });
});