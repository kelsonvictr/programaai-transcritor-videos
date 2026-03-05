"""
Worker de transcrição rápida.
Pipeline enxuto: extrair áudio → transcrever → salvar texto.
"""
import os
import subprocess
import threading
from datetime import datetime

import config
from database import update_transcription, get_transcription


def _log(log_path: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _set(tid, **kw):
    update_transcription(tid, kw)


def _fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def start_worker(tid: int):
    """Inicia processamento em thread separada."""
    t = threading.Thread(target=_run_pipeline, args=(tid,), daemon=True)
    t.start()


def _run_pipeline(tid: int):
    """Pipeline enxuto: probe -> extrair audio -> transcrever -> salvar texto."""
    rec = get_transcription(tid)
    if not rec:
        return

    output_dir = rec["output_dir"]
    input_path = rec["input_path"]
    log_path = os.path.join(output_dir, "logs.txt")
    model_path = rec.get("model_path") or config.WHISPER_MODEL_PATH
    language = rec.get("language") or config.DEFAULT_LANGUAGE

    os.makedirs(output_dir, exist_ok=True)

    _set(tid, status="PROCESSANDO", stage="INICIANDO", percent=5,
         started_at=datetime.now().isoformat(), log_path=log_path)
    _log(log_path, "Iniciando transcricao...")
    _log(log_path, f"Modelo: {os.path.basename(model_path)}")

    try:
        # PROBE
        _set(tid, stage="ANALISANDO", percent=10)
        _log(log_path, "Obtendo duracao do video...")
        duration = _probe_duration(input_path)
        dur_fmt = _fmt_ts(duration) if duration else "N/A"
        _set(tid, duration_seconds=duration)
        _log(log_path, f"Duracao: {dur_fmt}")

        # EXTRAIR AUDIO
        _set(tid, stage="EXTRAINDO AUDIO", percent=15)
        _log(log_path, "Convertendo para WAV 16kHz mono...")
        wav_path = os.path.join(output_dir, "audio.wav")
        _extract_audio(input_path, wav_path)
        _log(log_path, "Audio extraido!")

        # TRANSCREVER
        _set(tid, stage="TRANSCREVENDO", percent=25)
        _log(log_path, "Executando whisper-cli...")
        transcript = _transcribe(wav_path, model_path, language, output_dir, log_path)
        _set(tid, percent=90)
        _log(log_path, f"Transcricao concluida! ({len(transcript)} caracteres)")

        # SALVAR
        _set(tid, stage="FINALIZANDO", percent=95)
        _set(tid, transcript_txt=transcript)

        # DONE
        _set(tid, status="CONCLUIDA", stage="PRONTO", percent=100,
             finished_at=datetime.now().isoformat())
        _log(log_path, "Pronto!")

    except Exception as e:
        _set(tid, status="ERRO", stage="ERRO", error_message=str(e))
        _log(log_path, f"ERRO: {str(e)}")
        import traceback
        _log(log_path, traceback.format_exc())


def _probe_duration(input_path):
    cmd = [
        config.FFPROBE_BIN, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe falhou: {result.stderr}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"Duracao invalida: {result.stdout}")


def _extract_audio(input_path, wav_path):
    cmd = [
        config.FFMPEG_BIN, "-y", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        wav_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou (code {result.returncode})")


def _transcribe(wav_path, model_path, language, output_dir, log_path):
    """Executa whisper-cli com configuracoes otimizadas para velocidade."""
    import multiprocessing
    n_threads = multiprocessing.cpu_count()

    cmd = [
        config.WHISPER_BIN,
        "-m", model_path,
        "-f", wav_path,
        "-l", language,
        "-otxt",
        "-t", str(n_threads),
        "-bo", "1",
        "-bs", "1",
        "--no-fallback",
        "-pp",
    ]

    if not config.WHISPER_USE_GPU:
        cmd.append("--no-gpu")

    _log(log_path, f"Usando {n_threads} threads | beam=1 | greedy")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=output_dir,
        bufsize=1,
        universal_newlines=True
    )

    output_lines = []
    for line in process.stdout:
        line = line.rstrip()
        if line:
            output_lines.append(line)
            if "%" in line or "whisper" in line.lower():
                _log(log_path, f"  {line}")

    process.wait(timeout=7200)

    if process.returncode != 0:
        raise RuntimeError(f"whisper-cli falhou (code {process.returncode})")

    # Ler texto gerado pelo whisper
    transcript = ""
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        if fname.endswith(".wav.txt") or (fname.endswith(".txt") and "audio" in fname.lower()):
            with open(fpath, "r", encoding="utf-8") as f:
                transcript = f.read().strip()
            break

    if not transcript:
        for fname in sorted(os.listdir(output_dir)):
            if fname.endswith(".txt") and fname != "logs.txt":
                fpath = os.path.join(output_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    transcript = content
                    break

    if not transcript:
        transcript = "\n".join(output_lines)

    return transcript
