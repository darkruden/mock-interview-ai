import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, RefreshCw, Cpu, Activity, CheckCircle, AlertTriangle } from 'lucide-react';

// --- CONFIGURAÇÃO ---
// COLE SUA URL AQUI (ex: https://xyz.execute-api.us-east-1.amazonaws.com)
const API_BASE_URL = "https://731flytpdj.execute-api.us-east-1.amazonaws.com"; 

export default function App() {
  const [status, setStatus] = useState('idle'); // idle, recording, processing, completed, error
  const [sessionData, setSessionData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // --- LÓGICA DE ÁUDIO ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = handleUpload;
      mediaRecorderRef.current.start();
      setStatus('recording');
    } catch (err) {
      alert("Erro ao acessar microfone. Verifique as permissões.");
      console.error(err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setStatus('processing');
    }
  };

  // --- INTEGRAÇÃO COM BACKEND ---
  const handleUpload = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mpeg' });
    
    try {
      // 1. Handshake
      const initRes = await fetch(`${API_BASE_URL}/sessions`, {
        method: 'POST',
        body: JSON.stringify({ candidate_name: "React User" })
      });
      const initData = await initRes.json();
      
      if (!initData.upload_url) throw new Error("Falha na API de upload");

      // 2. Upload S3
      await fetch(initData.upload_url, {
        method: 'PUT',
        body: audioBlob,
        headers: { 'Content-Type': 'audio/mpeg' }
      });

      // 3. Polling
      pollResults(initData.session_id);

    } catch (err) {
      console.error(err);
      setStatus('error');
      setErrorMsg("Falha na conexão com a IA.");
    }
  };

  const pollResults = (sessionId) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
        const data = await res.json();

        if (data.status === 'COMPLETED') {
          clearInterval(interval);
          setSessionData(data);
          setStatus('completed');
        } else if (data.status === 'ERROR') {
          clearInterval(interval);
          setStatus('error');
          setErrorMsg(data.error_message || "Erro desconhecido na IA");
        }
        
        if (attempts > 30) { // Timeout de 60s
          clearInterval(interval);
          setStatus('error');
          setErrorMsg("A IA demorou muito para responder.");
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  // --- COMPONENTES VISUAIS ---
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
      
      {/* BACKGROUND EFFECTS */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-neon-purple/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-neon-blue/20 blur-[120px] rounded-full" />
      </div>

      <div className="z-10 w-full max-w-2xl text-center">
        
        {/* HEADER */}
        <motion.div 
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="mb-12"
        >
          <h1 className="text-5xl font-mono font-bold tracking-tighter bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
            MOCK.AI
          </h1>
          <p className="text-gray-400 mt-2 font-light tracking-widest text-sm">
            SIMULADOR DE ENTREVISTA NEURAL
          </p>
        </motion.div>

        {/* MAIN CONTENT AREA */}
        <AnimatePresence mode="wait">
          
          {/* ESTADO 1: IDLE / RECORDING */}
          {(status === 'idle' || status === 'recording') && (
            <motion.div 
              key="recorder"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center"
            >
              <div className="relative group">
                {/* Animação do "Pulse" ao gravar */}
                {status === 'recording' && (
                  <motion.div 
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                    className="absolute inset-0 bg-red-500 rounded-full blur-xl opacity-50"
                  />
                )}
                
                <button
                  onClick={status === 'idle' ? startRecording : stopRecording}
                  className={`relative w-32 h-32 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                    status === 'recording' 
                      ? 'border-red-500 bg-red-500/10 text-red-500 shadow-[0_0_30px_rgba(239,68,68,0.4)]' 
                      : 'border-neon-blue bg-neon-blue/10 text-neon-blue hover:shadow-[0_0_30px_rgba(0,243,255,0.4)] hover:scale-105'
                  }`}
                >
                  {status === 'idle' ? <Mic size={40} /> : <Square size={40} fill="currentColor" />}
                </button>
              </div>

              <p className="mt-8 text-lg font-mono text-gray-300">
                {status === 'idle' ? "Clique para começar a responder" : "Gravando... Clique para finalizar"}
              </p>
            </motion.div>
          )}

          {/* ESTADO 2: PROCESSING (O "GIF" GERADO POR CÓDIGO) */}
          {status === 'processing' && (
            <motion.div 
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center"
            >
              <div className="w-32 h-32 flex items-center justify-center relative">
                <motion.div 
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
                  className="absolute inset-0 border-t-2 border-neon-purple rounded-full"
                />
                <motion.div 
                  animate={{ rotate: -360 }}
                  transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                  className="absolute inset-2 border-r-2 border-neon-blue rounded-full"
                />
                <Cpu size={40} className="text-white animate-pulse" />
              </div>
              <h2 className="mt-6 text-2xl font-bold text-white">Analisando Perfil</h2>
              <p className="text-neon-blue animate-pulse mt-2">Processando voz e contexto...</p>
            </motion.div>
          )}

          {/* ESTADO 3: COMPLETED */}
          {status === 'completed' && sessionData && (
            <motion.div 
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full text-left"
            >
              <div className="grid grid-cols-2 gap-4 mb-6">
                <ScoreCard title="Técnica" value={sessionData.ai_feedback.technical_score} color="text-neon-blue" />
                <ScoreCard title="Clareza" value={sessionData.ai_feedback.clarity_score} color="text-neon-purple" />
              </div>

              <div className="bg-card-bg border border-white/10 p-6 rounded-xl backdrop-blur-sm mb-6">
                <h3 className="text-gray-400 text-sm uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Activity size={16} /> Resumo
                </h3>
                <p className="text-gray-200 leading-relaxed">
                  {sessionData.ai_feedback.summary}
                </p>
              </div>

              <div className="bg-card-bg border-l-4 border-neon-blue p-6 rounded-r-xl backdrop-blur-sm">
                 <h3 className="text-gray-400 text-sm uppercase tracking-wider mb-2 flex items-center gap-2">
                  <CheckCircle size={16} /> Feedback
                </h3>
                <p className="text-gray-300 text-sm leading-relaxed">
                  {sessionData.ai_feedback.feedback}
                </p>
              </div>

              <button 
                onClick={() => setStatus('idle')}
                className="mt-8 w-full py-4 border border-white/20 rounded-lg hover:bg-white/5 transition-colors flex items-center justify-center gap-2 font-mono text-sm"
              >
                <RefreshCw size={16} /> NOVA ENTREVISTA
              </button>
            </motion.div>
          )}

           {/* ESTADO 4: ERROR */}
           {status === 'error' && (
            <motion.div key="error" className="text-center text-red-400">
              <AlertTriangle size={64} className="mx-auto mb-4" />
              <h2 className="text-xl font-bold">Erro no Processamento</h2>
              <p className="mt-2">{errorMsg}</p>
              <button onClick={() => setStatus('idle')} className="mt-6 underline">Tentar Novamente</button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}

// Subcomponente simples para os Cards de Nota
function ScoreCard({ title, value, color }) {
  return (
    <div className="bg-card-bg border border-white/10 p-6 rounded-xl flex flex-col items-center justify-center relative overflow-hidden group">
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity bg-current ${color}`} />
      <span className="text-gray-400 text-sm uppercase tracking-wider">{title}</span>
      <span className={`text-5xl font-bold mt-2 ${color}`}>{value}</span>
    </div>
  );
}