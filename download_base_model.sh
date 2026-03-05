#!/bin/bash
# Baixa o modelo ggml-base.bin (~150MB) — muito mais rápido que small/medium
echo "⬇️  Baixando modelo base (~150MB)..."
curl -L -o ggml-base.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
echo "✅ Modelo base baixado!"
echo "   Tamanho: $(du -h ggml-base.bin | cut -f1)"
