import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, RefreshCw, Cpu, Activity, CheckCircle, AlertTriangle } from 'lucide-react';

// --- CONFIGURAÇÃO ---
// ⚠️ TROQUE PELA SUA URL DO TERRAFORM (sem a barra / no final)
const API_BASE_URL = "https://731flytpdj.execute-api.us-east-1.amazonaws.com"; 

export default function App() {
  const [status, setStatus] = useState('idle'); 
  const [sessionData, setSessionData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [jobDescription, setJobDescription] = useState("");
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // --- LÓGICA DE ÁUDIO ---
  const startRecording = async () => {
    console.log("Iniciando gravação...");
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
      alert("Erro ao acessar microfone. Verifique se o site é HTTPS ou localhost.");
      console.error(err);
    }
  };

  const stopRecording = () => {
    console.log("Parando gravação...");
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setStatus('processing');
    }
  };

  // --- INTEGRAÇÃO ---
  const handleUpload = async () => {
    console.log("Enviando áudio...");
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mpeg' });
    
    try {
      // 1. Handshake
      const initRes = await fetch(`${API_BASE_URL}/sessions`, {
        method: 'POST',
        body: JSON.stringify({ candidate_name: "React User", job_description: jobDescription })
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
      setErrorMsg("Falha na conexão. Verifique o console (F12).");
    }
  };

  const pollResults = (sessionId) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
        const data = await res.json();
        console.log("Polling status:", data.status);

        if (data.status === 'COMPLETED') {
          clearInterval(interval);
          setSessionData(data);
          setStatus('completed');
        } else if (data.status === 'ERROR') {
          clearInterval(interval);
          setStatus('error');
          setErrorMsg(data.error_message);
        }
        
        if (attempts > 30) { 
          clearInterval(interval);
          setStatus('error');
          setErrorMsg("Timeout: IA demorou muito.");
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  // --- RENDERIZAÇÃO ---
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden bg-dark-bg text-white font-sans">
      
      {/* HEADER */}
      <div className="z-10 mb-12 text-center">
        <h1 className="text-5xl font-mono font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple">
          MOCK.AI
        </h1>
        <p className="text-gray-400 mt-2 font-light tracking-widest text-sm">SIMULADOR NEURAL v1.0</p>
      </div>

      <AnimatePresence mode="wait">
        
        {/* ESTADO 1: GRAVADOR (BOTÃO) */}
        {(status === 'idle' || status === 'recording') && (
          <motion.div 
            key="recorder"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex flex-col items-center z-10"
          >
          {status === 'idle' && (
              <div className="w-full max-w-md mb-8 px-4">
                <textarea
                  className="w-full bg-black/40 text-white border border-neon-blue/30 rounded-lg p-4 focus:outline-none focus:border-neon-blue focus:ring-1 focus:ring-neon-blue transition-all resize-none placeholder-gray-500 text-sm font-mono"
                  rows="3"
                  placeholder="[OPCIONAL] Cole a Descrição da Vaga aqui..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                />
              </div>
            )}

            <button
              onClick={status === 'idle' ? startRecording : stopRecording}
              className={`w-32 h-32 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                status === 'recording' 
                  ? 'border-red-500 bg-red-500/20 shadow-[0_0_40px_red] animate-pulse' 
                  : 'border-neon-blue hover:bg-neon-blue/10 hover:shadow-[0_0_40px_#00f3ff]'
              }`}
            >
              {status === 'idle' ? <Mic size={40} className="text-neon-blue"/> : <Square size={40} className="text-red-500"/>}
            </button>
            <p className="mt-8 text-gray-400 font-mono">
              {status === 'idle' ? "CLIQUE PARA INICIAR" : "GRAVANDO... CLIQUE PARA PARAR"}
            </p>
          </motion.div>
        )}

        {/* ESTADO 2: PROCESSANDO (SPINNER) */}
        {status === 'processing' && (
          <motion.div 
            key="processing"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex flex-col items-center z-10"
          >
            <Cpu size={64} className="text-neon-purple animate-bounce mb-4" />
            <h2 className="text-2xl font-bold">Processando...</h2>
          </motion.div>
        )}

        {/* ESTADO 3: RESULTADOS */}
        {status === 'completed' && sessionData && (
          <motion.div 
            key="results"
            initial={{ opacity: 0, y: 50 }} animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl z-10 space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 border border-white/10 rounded-xl bg-card-bg text-center">
                <div className="text-gray-400 text-xs uppercase">Técnica</div>
                <div className="text-4xl font-bold text-neon-blue mt-2">{sessionData.ai_feedback.technical_score}</div>
              </div>
              <div className="p-6 border border-white/10 rounded-xl bg-card-bg text-center">
                <div className="text-gray-400 text-xs uppercase">Clareza</div>
                <div className="text-4xl font-bold text-neon-purple mt-2">{sessionData.ai_feedback.clarity_score}</div>
              </div>
            </div>

            <div className="p-6 border-l-4 border-neon-blue bg-card-bg rounded-r-xl">
              <h3 className="text-gray-400 text-xs uppercase mb-2 flex gap-2"><CheckCircle size={14}/> Feedback</h3>
              <p className="text-gray-300 leading-relaxed">{sessionData.ai_feedback.feedback}</p>
            </div>

            <button 
              onClick={() => setStatus('idle')}
              className="w-full py-4 mt-4 border border-white/20 rounded-lg hover:bg-white/10 transition-colors flex justify-center gap-2 items-center"
            >
              <RefreshCw size={16}/> Nova Entrevista
            </button>
          </motion.div>
        )}

        {/* ESTADO 4: ERRO */}
        {status === 'error' && (
           <div className="text-red-500 text-center z-10">
             <AlertTriangle size={48} className="mx-auto mb-2"/>
             <p>{errorMsg}</p>
             <button onClick={() => setStatus('idle')} className="mt-4 underline">Tentar de novo</button>
           </div>
        )}

      </AnimatePresence>
    </div>
  );
}