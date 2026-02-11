#!/bin/bash

# ══════════════════════════════════════════════════════════
# 🎓 Transcritor de Aulas → NotebookLM PRO
# Script ALL-IN-ONE (setup + run)
# ══════════════════════════════════════════════════════════

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  🎓 Transcritor de Aulas → NotebookLM PRO"
echo "  🚀 SETUP + RUN (All-in-One)"
echo "══════════════════════════════════════════════════════════"
echo ""

# ── Verificar Python ──────────────────────────────────────
echo -e "${BLUE}[1/6]${NC} Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado!${NC}"
    echo "   Instale com: brew install python@3.11"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"

# ── Verificar FFmpeg ──────────────────────────────────────
echo -e "${BLUE}[2/6]${NC} Verificando FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  FFmpeg não encontrado. Instalando...${NC}"
    brew install ffmpeg
else
    echo -e "${GREEN}✅ FFmpeg OK${NC}"
fi

# ── Verificar whisper-cli ─────────────────────────────────
echo -e "${BLUE}[3/6]${NC} Verificando whisper-cli..."
if ! command -v whisper-cli &> /dev/null; then
    echo -e "${YELLOW}⚠️  whisper-cli não encontrado. Instalando...${NC}"
    brew install whisper-cpp
else
    echo -e "${GREEN}✅ whisper-cli OK${NC}"
fi

# ── Verificar modelo GGML ─────────────────────────────────
echo -e "${BLUE}[4/6]${NC} Verificando modelo GGML..."
if [ ! -f "ggml-medium.bin" ]; then
    echo -e "${YELLOW}⚠️  Modelo não encontrado${NC}"
    echo ""
    read -p "   Baixar modelo agora? (~1.5 GB) [s/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "   Baixando..."
        curl -L --progress-bar -o ggml-medium.bin \
            https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
        echo -e "${GREEN}✅ Modelo baixado!${NC}"
    else
        echo -e "${RED}⚠️  Continuando sem modelo (transcrição não funcionará)${NC}"
    fi
else
    echo -e "${GREEN}✅ Modelo OK${NC}"
fi

# ── Configurar ambiente virtual ──────────────────────────
echo -e "${BLUE}[5/6]${NC} Configurando ambiente Python..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Ambiente OK${NC}"

# ── Inicializar banco ────────────────────────────────────
echo -e "${BLUE}[6/6]${NC} Inicializando banco de dados..."
python3 -c "from database import init_db; init_db()" 2>/dev/null || true
echo -e "${GREEN}✅ Banco OK${NC}"

echo ""
echo "══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Setup completo! Iniciando servidor...${NC}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo -e "   ${BLUE}🌐 Acesse: http://127.0.0.1:5000${NC}"
echo ""
echo "   Pressione ${RED}Ctrl+C${NC} para parar"
echo ""
echo "══════════════════════════════════════════════════════════"
echo ""

# ── Rodar Flask ───────────────────────────────────────────
python app.py
