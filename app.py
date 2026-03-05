"""
Transcritor de Vídeos — Versão Rápida
Aplicação Flask minimalista para transcrição de vídeos/áudios.
"""
import os
import shutil
import subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort
)

import config
from database import init_db, create_transcription, get_transcription, \
    list_transcriptions, update_transcription, delete_transcription
from worker import start_worker

# ══════════════════════════════════════════════════════════
#  SETUP
# ══════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

os.makedirs(config.UPLOADS_DIR, exist_ok=True)
os.makedirs(config.OUTPUTS_DIR, exist_ok=True)

init_db()


def _check_dependencies():
    issues = []
    if not os.path.isfile(config.WHISPER_BIN):
        issues.append(f"whisper-cli não encontrado em: {config.WHISPER_BIN}")
    try:
        subprocess.run([config.FFMPEG_BIN, "-version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append(f"ffmpeg não encontrado: {config.FFMPEG_BIN}")
    try:
        subprocess.run([config.FFPROBE_BIN, "-version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append(f"ffprobe não encontrado: {config.FFPROBE_BIN}")
    if not os.path.isfile(config.WHISPER_MODEL_PATH):
        issues.append(f"Modelo GGML não encontrado em: {config.WHISPER_MODEL_PATH}")
    return issues


STARTUP_ISSUES = _check_dependencies()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════
#  ROTAS
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    search = request.args.get("q", "")
    items = list_transcriptions(search=search or None)
    return render_template("index.html", items=items, search=search, issues=STARTUP_ISSUES)


@app.route("/new", methods=["GET", "POST"])
def new_form():
    if request.method == "GET":
        return render_template("new.html", issues=STARTUP_ISSUES)

    # POST — processar upload
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "danger")
        return redirect(url_for("new_form"))

    file = request.files["file"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado.", "danger")
        return redirect(url_for("new_form"))

    if not allowed_file(file.filename):
        flash(f"Formato não aceito. Use: {', '.join(config.ALLOWED_EXTENSIONS)}", "danger")
        return redirect(url_for("new_form"))

    title = request.form.get("title", "").strip() or file.filename
    language = request.form.get("language", config.DEFAULT_LANGUAGE).strip()

    # Salvar arquivo
    safe_name = secure_filename(file.filename)
    now = datetime.now()
    upload_path = os.path.join(config.UPLOADS_DIR, f"{now.strftime('%Y%m%d_%H%M%S')}_{safe_name}")
    file.save(upload_path)

    # Criar registro
    tid = create_transcription({
        "title": title,
        "original_filename": file.filename,
        "input_path": upload_path,
        "output_dir": "",
        "created_at": now.isoformat(),
        "status": "PENDENTE",
        "stage": "UPLOAD_OK",
        "percent": 0,
        "language": language,
        "model_path": config.WHISPER_MODEL_PATH,
    })

    output_dir = os.path.join(config.OUTPUTS_DIR, str(tid))
    os.makedirs(output_dir, exist_ok=True)
    update_transcription(tid, {"output_dir": output_dir})

    start_worker(tid)

    flash(f"Transcrição #{tid} iniciada!", "success")
    return redirect(url_for("detail", tid=tid))


@app.route("/t/<int:tid>")
def detail(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)

    # Duração formatada
    dur = rec.get("duration_seconds")
    if dur:
        h = int(dur // 3600)
        m = int((dur % 3600) // 60)
        s = int(dur % 60)
        rec["duration_fmt"] = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        rec["duration_fmt"] = ""

    # Log tail
    log_tail = ""
    log_path = rec.get("log_path")
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            log_tail = "".join(lines[-20:])

    return render_template("detail.html", rec=rec, log_tail=log_tail)


@app.route("/api/t/<int:tid>/status")
def api_status(tid):
    rec = get_transcription(tid)
    if not rec:
        return jsonify({"error": "Não encontrado"}), 404

    log_lines = []
    log_path = rec.get("log_path")
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_lines = f.readlines()[-15:]

    return jsonify({
        "id": tid,
        "status": rec["status"],
        "stage": rec["stage"],
        "percent": rec["percent"],
        "transcript_txt": rec.get("transcript_txt") or "",
        "error_message": rec.get("error_message"),
        "last_log_lines": [l.rstrip() for l in log_lines],
    })


@app.route("/t/<int:tid>/delete", methods=["POST"])
def delete(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)

    output_dir = rec.get("output_dir")
    if output_dir and os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    input_path = rec.get("input_path")
    if input_path and os.path.isfile(input_path):
        os.remove(input_path)

    delete_transcription(tid)
    flash(f"Transcrição #{tid} deletada.", "info")
    return redirect(url_for("index"))


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  🎙️ Transcritor de Vídeos — Versão Rápida")
    print("=" * 50)

    if STARTUP_ISSUES:
        print("\n⚠️  AVISOS:")
        for issue in STARTUP_ISSUES:
            print(f"   ❌ {issue}")
    else:
        print("\n✅ Tudo OK!")

    print(f"\n  📁 Data: {config.DATA_DIR}")
    print(f"  🤖 Modelo: {config.WHISPER_MODEL_PATH}")
    print()

    app.run(debug=True, host="127.0.0.1", port=5001)
