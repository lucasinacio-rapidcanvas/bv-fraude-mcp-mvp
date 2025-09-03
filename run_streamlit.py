#!/usr/bin/env python3
"""
Script para executar o app Streamlit
"""

import subprocess
import sys
import os

def main():
    """Executa o app Streamlit"""
    print("🚗 Iniciando Sistema de Verificação de Fraude em Lojistas...")
    print("📱 Interface Web: Streamlit")
    print("=" * 60)
    
    # Verifica se o arquivo existe
    streamlit_file = "app.py"
    if not os.path.exists(streamlit_file):
        print(f"❌ Erro: Arquivo {streamlit_file} não encontrado!")
        sys.exit(1)
    
    try:
        # Executa o Streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", streamlit_file, "--server.port", "8501"]
        print(f"🚀 Executando: {' '.join(cmd)}")
        print("🌐 URL: http://localhost:8501")
        print("⏹️  Para parar: Ctrl+C")
        print("=" * 60)
        
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Aplicação interrompida pelo usuário")
        sys.exit(0)

if __name__ == "__main__":
    main()