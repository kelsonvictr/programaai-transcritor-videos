#!/bin/bash

# ══════════════════════════════════════════════════════════
# 🎓 Transcritor de Aulas → NotebookLM PRO
# Menu de ajuda
# ══════════════════════════════════════════════════════════

# Cores
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo ""
echo "══════════════════════════════════════════════════════════"
echo -e "  ${BLUE}🎓 Transcritor de Aulas → NotebookLM PRO${NC}"
echo "══════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}📖 GUIA RÁPIDO${NC}"
echo ""
echo -e "${CYAN}┌─ Primeira Vez (Setup + Run)${NC}"
echo -e "${CYAN}│${NC}"
echo -e "${CYAN}│${NC}  ${YELLOW}./go.sh${NC}"
echo -e "${CYAN}│${NC}  ↳ Configura tudo e já inicia o servidor"
echo -e "${CYAN}│${NC}"
echo -e "${CYAN}└─ Acesse: ${BLUE}http://127.0.0.1:5000${NC}"
echo ""
echo -e "${CYAN}┌─ Modo em 2 Etapas${NC}"
echo -e "${CYAN}│${NC}"
echo -e "${CYAN}│${NC}  ${YELLOW}./start.sh${NC}  → Setup (só uma vez)"
echo -e "${CYAN}│${NC}  ${YELLOW}./run.sh${NC}    → Rodar servidor"
echo -e "${CYAN}│${NC}"
echo -e "${CYAN}└─ Acesse: ${BLUE}http://127.0.0.1:5000${NC}"
echo ""
echo "──────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}🛠 SCRIPTS DISPONÍVEIS${NC}"
echo ""
echo -e "  ${YELLOW}./go.sh${NC}      → All-in-one (setup + run)"
echo -e "  ${YELLOW}./start.sh${NC}   → Setup inicial"
echo -e "  ${YELLOW}./run.sh${NC}     → Rodar servidor"
echo -e "  ${YELLOW}./clean.sh${NC}   → Limpar dados"
echo -e "  ${YELLOW}./help.sh${NC}    → Mostrar esta ajuda"
echo ""
echo "──────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}📚 DOCUMENTAÇÃO${NC}"
echo ""
echo -e "  ${CYAN}QUICK_START.md${NC}  → Guia visual rápido"
echo -e "  ${CYAN}README.md${NC}       → Documentação completa"
echo ""
echo "──────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}❓ PROBLEMAS COMUNS${NC}"
echo ""
echo -e "${RED}Modelo não encontrado?${NC}"
echo -e "  ${YELLOW}curl -L -o ggml-medium.bin \\${NC}"
echo -e "  ${YELLOW}https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin${NC}"
echo ""
echo -e "${RED}whisper-cli não encontrado?${NC}"
echo -e "  ${YELLOW}brew install whisper-cpp${NC}"
echo ""
echo -e "${RED}FFmpeg não encontrado?${NC}"
echo -e "  ${YELLOW}brew install ffmpeg${NC}"
echo ""
echo "══════════════════════════════════════════════════════════"
echo ""
