import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Phone, PhoneOff, LogOut, Activity, Radio } from 'lucide-react';

// Autenticação
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';

// O Hook Mágico que criamos
import { useGeminiLive } from './hooks/useGeminiLive';

// --- CONFIGURAÇÃO ---
// ⚠️ Mantenha a URL da sua API Gateway aqui
const API_BASE_URL = "https://731flytpdj.execute-api.us-east-1.amazonaws.com";

export default function App() {
  // Inicializa o Hook da Live API
  const { status, isSpeaking, connect, disconnect } = useGeminiLive(API_BASE_URL);

  // --- RENDERIZAÇÃO ---
  return (
    <Authenticator
      loginMechanisms={['email']}
      signUpAttributes={['email']}
    >
      {({ signOut, user }) => (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden bg-dark-bg text-white font-sans">

          {/* BOTÃO DE LOGOUT (Canto Superior Direito) */}
          <button
            onClick={() => { disconnect(); signOut(); }}
            className="absolute top-6 right-6 z-50 text-xs text-gray-500 hover:text-red-400 flex items-center gap-2 transition-colors font-mono tracking-wider border border-white/5 px-3 py-2 rounded-full hover:border-red-500/30 hover:bg-red-500/10"
          >
            <LogOut size={14} /> SAIR <span className="opacity-50">|</span> {user?.username?.slice(0, 15)}...
          </button>

          {/* HEADER */}
          <div className="z-10 mb-8 text-center relative w-full max-w-2xl">
            <h1 className="text-5xl font-mono font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple">
              MOCK.LIVE
            </h1>
            <p className="text-gray-400 mt-2 font-light tracking-widest text-sm flex justify-center items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              {status === 'connected' ? 'SISTEMA ONLINE' : 'AGUARDANDO CONEXÃO'}
            </p>
          </div>

          <AnimatePresence mode="wait">

            {/* ESTADO 1: DESCONECTADO (Botão de Ligar) */}
            {(status === 'disconnected' || status === 'error') && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center z-10"
              >
                <div className="mb-8 text-center max-w-md">
                  <p className="text-gray-300">
                    Bem-vindo à entrevista em tempo real.
                    <br />
                    <span className="text-neon-blue font-bold">Sem delay. Sem upload.</span>
                  </p>
                </div>

                <button
                  onClick={connect}
                  className="group relative w-40 h-40 rounded-full border-2 border-neon-blue bg-black/50 flex items-center justify-center transition-all duration-300 hover:scale-105 hover:shadow-[0_0_50px_#00f3ff]"
                >
                  <div className="absolute inset-0 rounded-full border border-neon-blue opacity-50 animate-ping"></div>
                  <Phone size={48} className="text-neon-blue group-hover:text-white transition-colors" />
                </button>

                <p className="mt-8 text-gray-500 font-mono text-sm tracking-widest">CLIQUE PARA INICIAR</p>

                {status === 'error' && (
                  <p className="mt-4 text-red-500 bg-red-500/10 px-4 py-2 rounded">Erro na conexão. Tente novamente.</p>
                )}
              </motion.div>
            )}

            {/* ESTADO 2: CONECTANDO */}
            {status === 'connecting' && (
              <motion.div
                key="connecting"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center z-10"
              >
                <Radio size={64} className="text-neon-purple animate-bounce mb-4" />
                <h2 className="text-2xl font-bold text-neon-purple">Estabelecendo Link Seguro...</h2>
              </motion.div>
            )}

            {/* ESTADO 3: CONECTADO (Interface de Conversa) */}
            {status === 'connected' && (
              <motion.div
                key="connected"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center z-10 w-full max-w-md"
              >
                {/* VISUALIZADOR DE ÁUDIO (ORB) */}
                <div className="relative w-64 h-64 flex items-center justify-center mb-12">
                  {/* Círculo Central (Muda de cor se a IA estiver falando) */}
                  <motion.div
                    animate={{
                      scale: isSpeaking ? [1, 1.2, 1] : 1,
                      borderColor: isSpeaking ? '#a855f7' : '#00f3ff', // Roxo se IA fala, Azul se você ouve
                      boxShadow: isSpeaking ? '0 0 60px #a855f7' : '0 0 20px #00f3ff'
                    }}
                    transition={{ repeat: Infinity, duration: isSpeaking ? 0.5 : 2 }}
                    className="w-40 h-40 rounded-full border-4 bg-black/80 flex items-center justify-center z-10 transition-colors"
                  >
                    {isSpeaking ? (
                      <Activity size={64} className="text-neon-purple" />
                    ) : (
                      <Mic size={64} className="text-neon-blue animate-pulse" />
                    )}
                  </motion.div>

                  {/* Ondas de fundo */}
                  <div className={`absolute inset-0 rounded-full border border-white/10 ${isSpeaking ? 'animate-ping' : ''}`}></div>
                  <div className={`absolute inset-4 rounded-full border border-white/5 ${isSpeaking ? 'animate-pulse' : ''}`}></div>
                </div>

                {/* STATUS TEXTUAL */}
                <div className="text-center mb-12 h-16">
                  {isSpeaking ? (
                    <p className="text-neon-purple font-bold text-xl tracking-wider animate-pulse">A IA ESTÁ FALANDO...</p>
                  ) : (
                    <p className="text-neon-blue font-bold text-xl tracking-wider">ESCUTANDO VOCÊ...</p>
                  )}
                  <p className="text-gray-500 text-xs mt-2">Microfone Aberto</p>
                </div>

                {/* BOTÃO DE DESLIGAR */}
                <button
                  onClick={disconnect}
                  className="flex items-center gap-3 px-8 py-4 bg-red-500/20 border border-red-500 text-red-500 rounded-full hover:bg-red-500 hover:text-white transition-all duration-300 font-bold tracking-widest"
                >
                  <PhoneOff size={20} /> ENCERRAR CHAMADA
                </button>

              </motion.div>
            )}

          </AnimatePresence>
        </div>
      )}
    </Authenticator>
  );
}