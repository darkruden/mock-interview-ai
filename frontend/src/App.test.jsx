import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';

// --- 1. MOCK DO AWS AMPLIFY ---
// Simulamos que o usuário já está logado, renderizando direto o conteúdo filho
vi.mock('@aws-amplify/ui-react', () => ({
    Authenticator: ({ children }) => {
        return children({
            signOut: vi.fn(),
            user: { username: 'TestUser' }
        });
    }
}));

// --- 2. MOCK DO HOOK useGeminiLive ---
// Vamos controlar o estado da conexão manualmente nos testes
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();

// Por padrão, começamos desconectados
const mockUseGeminiLive = vi.fn(() => ({
    status: 'disconnected',
    isSpeaking: false,
    connect: mockConnect,
    disconnect: mockDisconnect
}));

vi.mock('./hooks/useGeminiLive', () => ({
    useGeminiLive: () => mockUseGeminiLive()
}));

describe('App Component (Interface Principal)', () => {

    it('deve renderizar a tela inicial (Desconectado) corretamente', () => {
        render(<App />);

        // Verifica textos iniciais
        expect(screen.getByText(/MOCK.LIVE/i)).toBeInTheDocument();
        expect(screen.getByText(/AGUARDANDO CONEXÃO/i)).toBeInTheDocument();
        expect(screen.getByText(/CLIQUE PARA INICIAR/i)).toBeInTheDocument();

        // Verifica se o botão de conectar está na tela (ícone de telefone)
        // Como é um ícone, buscamos pelo papel 'button'
        const startButton = screen.getByRole('button', { name: '' });
        // Nota: Se o botão tivesse texto seria mais fácil, mas ícones puros exigem busca por role
        expect(startButton).toBeInTheDocument();
    });

    it('deve chamar a função connect ao clicar no botão de iniciar', () => {
        render(<App />);

        // Encontra o botão principal (o círculo grande no meio)
        // Dica: Em projetos reais, adicionaríamos data-testid="start-btn" no botão para facilitar
        const buttons = screen.getAllByRole('button');
        const startButton = buttons.find(btn => btn.className.includes('w-40')); // Busca pelo estilo único do botão grande

        fireEvent.click(startButton);

        expect(mockConnect).toHaveBeenCalledTimes(1);
    });

    it('deve mostrar a interface de "SISTEMA ONLINE" quando conectado', () => {
        // Simulamos que o hook retornou status 'connected'
        mockUseGeminiLive.mockReturnValue({
            status: 'connected',
            isSpeaking: false,
            connect: mockConnect,
            disconnect: mockDisconnect
        });

        render(<App />);

        expect(screen.getByText(/SISTEMA ONLINE/i)).toBeInTheDocument();
        expect(screen.getByText(/ESCUTANDO VOCÊ/i)).toBeInTheDocument();
        expect(screen.getByText(/ENCERRAR CHAMADA/i)).toBeInTheDocument();
    });

    it('deve indicar visualmente quando a IA está falando', () => {
        // Simulamos status conectado E falando
        mockUseGeminiLive.mockReturnValue({
            status: 'connected',
            isSpeaking: true, // <--- MUDANÇA
            connect: mockConnect,
            disconnect: mockDisconnect
        });

        render(<App />);

        expect(screen.getByText(/A IA ESTÁ FALANDO/i)).toBeInTheDocument();
    });
});