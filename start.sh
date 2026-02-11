#!/bin/bash

# ══════════════════════════════════════════════════════════
# 🎓 Transcritor de Aulas → NotebookLM PRO
# Script de inicialização
# ══════════════════════════════════════════════════════════

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  🎓 Transcritor de Aulas → NotebookLM PRO"
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
echo ""

# ── Verificar FFmpeg ──────────────────────────────────────
echo -e "${BLUE}[2/6]${NC} Verificando FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  FFmpeg não encontrado!${NC}"
    echo "   Instalando via Homebrew..."
    brew install ffmpeg
else
    echo -e "${GREEN}✅ FFmpeg encontrado: $(which ffmpeg)${NC}"
fi
echo ""

# ── Verificar whisper-cli ─────────────────────────────────
echo -e "${BLUE}[3/6]${NC} Verificando whisper-cli..."
if ! command -v whisper-cli &> /dev/null; then
    echo -e "${YELLOW}⚠️  whisper-cli não encontrado!${NC}"
    echo "   Instalando via Homebrew..."
    brew install whisper-cpp
else
    echo -e "${GREEN}✅ whisper-cli encontrado: $(which whisper-cli)${NC}"
fi
echo ""

# ── Verificar modelo GGML ─────────────────────────────────
echo -e "${BLUE}[4/6]${NC} Verificando modelo GGML..."
if [ ! -f "ggml-medium.bin" ]; then
    echo -e "${YELLOW}⚠️  Modelo ggml-medium.bin não encontrado!${NC}"
    echo ""
    read -p "   Deseja baixar o modelo agora? (~1.5 GB) [s/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "   Baixando ggml-medium.bin..."
        curl -L --progress-bar -o ggml-medium.bin \
            https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
        echo -e "${GREEN}✅ Modelo baixado!${NC}"
    else
        echo -e "${RED}❌ Modelo não encontrado. Baixe manualmente:${NC}"
        echo "   curl -L -o ggml-medium.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin"
        echo ""
        echo -e "${YELLOW}   Continuando sem o modelo (a transcrição não funcionará)...${NC}"
    fi
else
    MODEL_SIZE=$(du -h ggml-medium.bin | cut -f1)
    echo -e "${GREEN}✅ Modelo encontrado: ggml-medium.bin ($MODEL_SIZE)${NC}"
fi
echo ""

# ── Configurar ambiente virtual ──────────────────────────
echo -e "${BLUE}[5/6]${NC} Configurando ambiente virtual Python..."
if [ ! -d ".venv" ]; then
    echo "   Criando .venv..."
    python3 -m venv .venv
    echo -e "${GREEN}✅ Ambiente virtual criado!${NC}"
else
    echo -e "${GREEN}✅ Ambiente virtual já existe${NC}"
fi

echo "   Ativando ambiente..."
source .venv/bin/activate

echo "   Instalando dependências..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Dependências instaladas!${NC}"
echo ""

# ── Inicializar banco de dados ───────────────────────────
echo -e "${BLUE}[6/6]${NC} Inicializando banco de dados..."
python3 -c "from database import init_db; init_db()" 2>/dev/null || true
echo -e "${GREEN}✅ Banco de dados pronto!${NC}"
echo ""

# ── Resumo final ──────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Tudo pronto!${NC}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "Deseja iniciar o servidor agora?"
echo ""
read -p "Iniciar Flask? [S/n]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${BLUE}🚀 Iniciando servidor...${NC}"
    echo ""
    echo "   Acesse: ${BLUE}http://127.0.0.1:5000${NC}"
    echo ""
    echo "   Pressione Ctrl+C para parar"
    echo ""
    python app.py
else
    echo ""
    echo "Para iniciar o servidor depois, execute:"
    echo ""
    echo -e "  ${BLUE}./run.sh${NC}"
    echo -e "  ${YELLOW}ou${NC}"
    echo -e "  ${BLUE}python app.py${NC}"
    echo ""
    echo "Depois acesse: ${BLUE}http://127.0.0.1:5000${NC}"
    echo ""
fi
