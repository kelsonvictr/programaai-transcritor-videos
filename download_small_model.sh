#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
#  Download do Modelo Small (Recomendado para aulas >1h)
# ══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODEL_FILE="ggml-small.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  📥 Download do Modelo SMALL"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "  Tamanho: ~465 MB"
echo "  Velocidade: 4x mais rápido que medium"
echo "  Qualidade: Boa (recomendado para aulas longas)"
echo ""
echo "══════════════════════════════════════════════════════════"
echo ""

if [ -f "$MODEL_FILE" ]; then
    echo "✅ Modelo small já existe!"
    echo ""
    ls -lh "$MODEL_FILE"
    echo ""
    read -p "Deseja baixar novamente? (s/N): " choice
    case "$choice" in
        s|S|sim|SIM)
            echo "Removendo modelo antigo..."
            rm -f "$MODEL_FILE"
            ;;
        *)
            echo "Mantendo modelo existente."
            exit 0
            ;;
    esac
fi

echo "Baixando modelo small..."
echo ""

if command -v curl &> /dev/null; then
    curl -L --progress-bar "$MODEL_URL" -o "$MODEL_FILE"
elif command -v wget &> /dev/null; then
    wget --show-progress "$MODEL_URL" -O "$MODEL_FILE"
else
    echo "❌ ERRO: curl ou wget não encontrado"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════"
echo "✅ Download concluído!"
echo "══════════════════════════════════════════════════════════"
echo ""
ls -lh "$MODEL_FILE"
echo ""
echo "💡 O sistema agora usará automaticamente o modelo small."
echo "   Para voltar ao medium, renomeie ou delete ggml-small.bin"
echo ""
