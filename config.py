"""
Configurações do Transcritor de Aulas → NotebookLM PRO
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Binários ──────────────────────────────────────────────
WHISPER_BIN = os.environ.get("WHISPER_BIN", "/opt/homebrew/bin/whisper-cli")
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.environ.get("FFPROBE_BIN", "ffprobe")

# ── Modelo GGML ──────────────────────────────────────────
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "ggml-medium.bin"))

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

# ── Pós-processamento ───────────────────────────────────
DEFAULT_PARAGRAPH_GROUP_SIZE = 4       # legendas agrupadas por parágrafo
DEFAULT_CHAPTER_WINDOW_SECONDS = 240   # janela de 4 min p/ detecção de tópicos
DEFAULT_REELS_CUT_COUNT = 12           # cortes sugeridos para Reels

# ── Whisper VAD (Voice Activity Detection) ───────────────
# VAD ajuda a remover silêncios e melhorar timestamps em aulas longas
# Recomendado: deixar ativado por padrão (checkbox na UI)

# ── Whisper GPU/CPU ──────────────────────────────────────
# Se houver crash com Metal/GPU no Apple Silicon, mude para False
WHISPER_USE_GPU = os.environ.get("WHISPER_USE_GPU", "false").lower() == "true"

# ── Flask ────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "transcritor-local-dev-key-2025")
