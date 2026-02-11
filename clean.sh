#!/bin/bash

# ══════════════════════════════════════════════════════════
# 🎓 Transcritor de Aulas → NotebookLM PRO
# Script de limpeza/reset
# ══════════════════════════════════════════════════════════

# Cores
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  🧹 Limpeza do Projeto"
echo "══════════════════════════════════════════════════════════"
echo ""
echo -e "${YELLOW}⚠️  ATENÇÃO: Esta ação vai remover:${NC}"
echo ""
echo "   • Todas as transcrições do banco de dados"
echo "   • Todos os arquivos uploadados"
echo "   • Todos os pacotes gerados"
echo "   • Logs e arquivos temporários"
echo ""
echo -e "${RED}   Modelo GGML e ambiente virtual serão mantidos${NC}"
echo ""

read -p "Deseja continuar? [s/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operação cancelada."
    exit 0
fi

echo ""
echo "Limpando..."

# Remover data/
if [ -d "data" ]; then
    rm -rf data/
    echo -e "${GREEN}✅ Diretório data/ removido${NC}"
fi

# Remover __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✅ Cache Python limpo${NC}"

# Recriar estrutura
mkdir -p data/{uploads,outputs}
echo -e "${GREEN}✅ Estrutura recriada${NC}"

# Reinicializar banco
if [ -d ".venv" ]; then
    source .venv/bin/activate
    python3 -c "from database import init_db; init_db()" 2>/dev/null
    echo -e "${GREEN}✅ Banco de dados reinicializado${NC}"
fi

echo ""
echo -e "${GREEN}✅ Limpeza concluída!${NC}"
echo ""
echo "O projeto está pronto para uso limpo."
echo "Execute: ./run.sh"
echo ""
