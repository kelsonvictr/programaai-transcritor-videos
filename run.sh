#!/bin/bash

# ══════════════════════════════════════════════════════════
# 🎓 Transcritor de Aulas → NotebookLM PRO
# Script para rodar o servidor
# ══════════════════════════════════════════════════════════

# Cores
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  🎓 Transcritor de Aulas → NotebookLM PRO"
echo "══════════════════════════════════════════════════════════"
echo ""

# Ativar ambiente virtual
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "   Execute primeiro: ./start.sh"
    exit 1
fi

source .venv/bin/activate

echo -e "${GREEN}✅ Ambiente ativado${NC}"
echo ""
echo -e "${BLUE}🚀 Iniciando servidor Flask...${NC}"
echo ""
echo "   Acesse: http://127.0.0.1:5000"
echo ""
echo "   Pressione Ctrl+C para parar"
echo ""

# Rodar servidor
python app.py
