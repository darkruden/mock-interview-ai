import sys
import os
import json
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(backend_root)
# --- CONFIGURAÇÃO DE AMBIENTE ---
# Tenta carregar variáveis do .env se existir (instale com: pip install python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Adiciona o diretório atual ao path para conseguir importar 'src'
# Isso permite rodar o script de dentro da pasta backend/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gemini_token_fix():
    print("🧪 INICIANDO TESTE LOCAL: Geração de Token Gemini (Correção Erro 1007)")
    print("-" * 60)

    # 1. Verifica API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERRO: Variável GEMINI_API_KEY não encontrada.")
        print("   -> Crie um arquivo .env na pasta backend/ com: GEMINI_API_KEY=AIza...")
        print("   -> Ou exporte no terminal: export GEMINI_API_KEY='sua_chave'")
        return

    # 2. Importa a Lambda (Lazy import para garantir que o path esteja certo)
    try:
        from src.handlers.get_gemini_token import lambda_handler
    except ImportError as e:
        print(f"❌ ERRO DE IMPORTAÇÃO: {e}")
        print("   Certifique-se de estar rodando este script de DENTRO da pasta backend/")
        return

    # 3. Executa a Lambda (Simulação)
    print("🔄 Executando lambda_handler localmente...")
    try:
        # Evento e Contexto vazios (não são usados nesta função)
        response = lambda_handler({}, None)
    except Exception as e:
        print(f"❌ ERRO NA EXECUÇÃO: {str(e)}")
        return

    # 4. Valida a Resposta HTTP
    if response['statusCode'] != 200:
        print(f"❌ FALHA: A Lambda retornou erro {response['statusCode']}")
        print(f"   Detalhes: {response['body']}")
        return

    # 5. Valida o Token (O Teste Real)
    body = json.loads(response['body'])
    token = body.get('token')
    
    print(f"✅ Lambda respondeu com sucesso.")
    print(f"   Token recebido: {token[:20]}... (truncado)")

    if token.startswith("authTokens/"):
        print("\n🚫 FALHA CRÍTICA (FORMATO ERRADO):")
        print("   O token AINDA contém o prefixo 'authTokens/'.")
        print("   O WebSocket do Google VAI REJEITAR este token (Erro 1007).")
        print("   -> Verifique se o .replace('authTokens/', '') está no código.")
    else:
        print("\n✨ SUCESSO TOTAL (CORREÇÃO VALIDADA):")
        print("   O token está LIMPO (sem prefixo).")
        print("   Este token está pronto para ser aceito pelo WebSocket da Live API.")

if __name__ == "__main__":
    test_gemini_token_fix()