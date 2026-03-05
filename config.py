"""
Configurações do Transcritor de Vídeos — Versão Rápida
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Binários ──────────────────────────────────────────────
WHISPER_BIN = os.environ.get("WHISPER_BIN", "/opt/homebrew/bin/whisper-cli")
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.environ.get("FFPROBE_BIN", "ffprobe")

# ── Modelo GGML ──────────────────────────────────────────
# Base: mais rápido (~10x que medium), qualidade suficiente p/ transcrição
# Small: bom equilíbrio | Medium: melhor qualidade, mais lento
WHISPER_MODEL_PATH = os.environ.get(
    "WHISPER_MODEL_PATH",
    os.path.join(BASE_DIR, "ggml-base.bin")
)

# Fallback: se não tiver base, tenta small, depois medium
if not os.path.exists(WHISPER_MODEL_PATH):
    _small = os.path.join(BASE_DIR, "ggml-small.bin")
    _medium = os.path.join(BASE_DIR, "ggml-medium.bin")
    if os.path.exists(_small):
        WHISPER_MODEL_PATH = _small
    elif os.path.exists(_medium):
        WHISPER_MODEL_PATH = _medium

# ── Idioma padrão ────────────────────────────────────────
DEFAULT_LANGUAGE = "pt"

# ── Diretórios ───────────────────────────────────────────
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
DB_PATH = os.path.join(DATA_DIR, "db.sqlite3")

# ── Upload ───────────────────────────────────────────────
MAX_UPLOAD_MB = 4096  # 4 GB
ALLOWED_EXTENSIONS = {"mov", "mp4", "m4a", "mp3", "wav", "mkv", "webm"}

# ── Whisper GPU/CPU ──────────────────────────────────────
WHISPER_USE_GPU = os.environ.get("WHISPER_USE_GPU", "false").lower() == "true"

# ── Flask ────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "transcritor-local-dev-key-2025")
