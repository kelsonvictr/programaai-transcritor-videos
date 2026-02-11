"""
Transcritor de Aulas → NotebookLM PRO
Aplicação Flask principal.
"""
import os
import json
import shutil
import subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_file, jsonify, abort
)

import config
from database import init_db, create_transcription, get_transcription, \
    list_transcriptions, update_transcription, delete_transcription
from worker import start_worker, _create_zip

# ══════════════════════════════════════════════════════════
#  SETUP
# ══════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

# Criar diretórios
os.makedirs(config.UPLOADS_DIR, exist_ok=True)
os.makedirs(config.OUTPUTS_DIR, exist_ok=True)

# Inicializar banco
init_db()


# ══════════════════════════════════════════════════════════
#  VALIDAÇÕES DE STARTUP
# ══════════════════════════════════════════════════════════

def _check_dependencies():
    """Verifica se as dependências externas estão disponíveis."""
    issues = []

    # whisper-cli
    if not os.path.isfile(config.WHISPER_BIN):
        issues.append(f"whisper-cli não encontrado em: {config.WHISPER_BIN}")

    # ffmpeg
    try:
        subprocess.run([config.FFMPEG_BIN, "-version"],
                      capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append(f"ffmpeg não encontrado: {config.FFMPEG_BIN}")

    # ffprobe
    try:
        subprocess.run([config.FFPROBE_BIN, "-version"],
                      capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        issues.append(f"ffprobe não encontrado: {config.FFPROBE_BIN}")

    # modelo
    if not os.path.isfile(config.WHISPER_MODEL_PATH):
        issues.append(f"Modelo GGML não encontrado em: {config.WHISPER_MODEL_PATH}")

    return issues


STARTUP_ISSUES = _check_dependencies()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════
#  ROTAS — DASHBOARD
# ══════════════════════════════════════════════════════════

@app.route("/")
def index():
    status_filter = request.args.get("status", "")
    tag_filter = request.args.get("tag", "")
    search = request.args.get("q", "")

    items = list_transcriptions(
        status=status_filter or None,
        tag=tag_filter or None,
        search=search or None,
    )

    # Parsear tags JSON para exibição
    for item in items:
        try:
            item["tags"] = json.loads(item.get("tags_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            item["tags"] = {}

    return render_template("index.html",
                         items=items,
                         status_filter=status_filter,
                         tag_filter=tag_filter,
                         search=search,
                         issues=STARTUP_ISSUES)


# ══════════════════════════════════════════════════════════
#  ROTAS — NOVA TRANSCRIÇÃO
# ══════════════════════════════════════════════════════════

@app.route("/new", methods=["GET"])
def new_form():
    return render_template("new.html", issues=STARTUP_ISSUES)


@app.route("/new", methods=["POST"])
def new_submit():
    # Validações
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "danger")
        return redirect(url_for("new_form"))

    file = request.files["file"]
    if file.filename == "":
        flash("Nenhum arquivo selecionado.", "danger")
        return redirect(url_for("new_form"))

    if not allowed_file(file.filename):
        flash(f"Extensão não permitida. Aceitas: {', '.join(config.ALLOWED_EXTENSIONS)}", "danger")
        return redirect(url_for("new_form"))

    title = request.form.get("title", "").strip() or file.filename
    curso = request.form.get("curso", "").strip()
    turma = request.form.get("turma", "").strip()
    modulo = request.form.get("modulo", "").strip()
    language = request.form.get("language", config.DEFAULT_LANGUAGE).strip()
    model_name = request.form.get("model_name", "medium").strip()
    use_vad = "use_vad" in request.form
    clean_text = "clean_text" in request.form
    add_timestamps = "add_timestamps" in request.form
    gen_notes = "gen_notes" in request.form
    gen_chapters = "gen_chapters" in request.form
    gen_reels = "gen_reels" in request.form

    tags = {}
    if curso:
        tags["curso"] = curso
    if turma:
        tags["turma"] = turma
    if modulo:
        tags["modulo"] = modulo

    # Salvar arquivo
    safe_name = secure_filename(file.filename)
    now = datetime.now()
    date_prefix = now.strftime("%Y%m%d_%H%M%S")

    upload_path = os.path.join(config.UPLOADS_DIR, f"{date_prefix}_{safe_name}")
    file.save(upload_path)

    # Criar registro no banco
    tid = create_transcription({
        "title": title,
        "tags_json": json.dumps(tags, ensure_ascii=False),
        "original_filename": file.filename,
        "input_path": upload_path,
        "output_dir": "",  # será definido abaixo
        "created_at": now.isoformat(),
        "status": "PENDENTE",
        "stage": "UPLOAD_OK",
        "percent": 0,
        "language": language,
        "use_vad": 1 if use_vad else 0,
        "clean_text": 1 if clean_text else 0,
        "add_timestamps": 1 if add_timestamps else 0,
        "gen_notes": 1 if gen_notes else 0,
        "gen_chapters": 1 if gen_chapters else 0,
        "gen_reels": 1 if gen_reels else 0,
        "model_name": model_name,
        "model_path": config.WHISPER_MODEL_PATH,
    })

    # Definir output_dir com ID
    output_dir = os.path.join(config.OUTPUTS_DIR, str(tid))
    os.makedirs(output_dir, exist_ok=True)
    update_transcription(tid, {"output_dir": output_dir})

    # Disparar worker
    start_worker(tid)

    flash(f"Transcrição #{tid} criada e processamento iniciado!", "success")
    return redirect(url_for("detail", tid=tid))


# ══════════════════════════════════════════════════════════
#  ROTAS — DETALHES
# ══════════════════════════════════════════════════════════

@app.route("/t/<int:tid>")
def detail(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)

    # Parsear tags
    try:
        rec["tags"] = json.loads(rec.get("tags_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        rec["tags"] = {}

    # Ler preview do transcript
    txt_preview = ""
    txt_path = rec.get("transcript_txt_path")
    if txt_path and os.path.isfile(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            txt_preview = f.read(2000)

    # Ler capítulos
    chapters_preview = ""
    ch_path = rec.get("chapters_md_path")
    if ch_path and os.path.isfile(ch_path):
        with open(ch_path, "r", encoding="utf-8") as f:
            chapters_preview = f.read()

    # Ler notas
    notes_previews = {}
    for key in ["notes_short_path", "notes_medium_path", "notes_detailed_path"]:
        path = rec.get(key)
        if path and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                notes_previews[key] = f.read(3000)

    # Ler reels
    reels_preview = ""
    r_path = rec.get("reels_md_path")
    if r_path and os.path.isfile(r_path):
        with open(r_path, "r", encoding="utf-8") as f:
            reels_preview = f.read()

    # Ler prompts
    prompts_preview = ""
    p_path = rec.get("prompts_txt_path")
    if p_path and os.path.isfile(p_path):
        with open(p_path, "r", encoding="utf-8") as f:
            prompts_preview = f.read()

    # Log tail
    log_tail = ""
    log_path = rec.get("log_path")
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            log_tail = "".join(lines[-30:])

    # Duração formatada
    dur = rec.get("duration_seconds")
    if dur:
        h = int(dur // 3600)
        m = int((dur % 3600) // 60)
        s = int(dur % 60)
        rec["duration_fmt"] = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        rec["duration_fmt"] = "N/A"

    return render_template("detail.html",
                         rec=rec,
                         txt_preview=txt_preview,
                         chapters_preview=chapters_preview,
                         notes_previews=notes_previews,
                         reels_preview=reels_preview,
                         prompts_preview=prompts_preview,
                         log_tail=log_tail)


# ══════════════════════════════════════════════════════════
#  ROTAS — API
# ══════════════════════════════════════════════════════════

@app.route("/api/t/<int:tid>/status")
def api_status(tid):
    rec = get_transcription(tid)
    if not rec:
        return jsonify({"error": "Não encontrado"}), 404

    # Log tail
    log_lines = []
    log_path = rec.get("log_path")
    if log_path and os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_lines = f.readlines()[-20:]

    return jsonify({
        "id": tid,
        "status": rec["status"],
        "stage": rec["stage"],
        "percent": rec["percent"],
        "duration_seconds": rec.get("duration_seconds"),
        "error_message": rec.get("error_message"),
        "last_log_lines": [l.rstrip() for l in log_lines],
    })


# ══════════════════════════════════════════════════════════
#  ROTAS — DOWNLOAD
# ══════════════════════════════════════════════════════════

FILE_KEYS = {
    "txt": "transcript_txt_path",
    "srt": "transcript_srt_path",
    "vtt": "transcript_vtt_path",
    "chapters_md": "chapters_md_path",
    "chapters_json": "chapters_json_path",
    "notes_short": "notes_short_path",
    "notes_medium": "notes_medium_path",
    "notes_detailed": "notes_detailed_path",
    "prompts": "prompts_txt_path",
    "reels_md": "reels_md_path",
    "reels_json": "reels_json_path",
    "index": "index_json_path",
    "readme": "readme_path",
    "zip": "zip_path",
    "log": "log_path",
}


@app.route("/t/<int:tid>/download/<filekey>")
def download_file(tid, filekey):
    rec = get_transcription(tid)
    if not rec:
        abort(404)

    db_key = FILE_KEYS.get(filekey)
    if not db_key:
        abort(404)

    file_path = rec.get(db_key)
    if not file_path or not os.path.isfile(file_path):
        # Tentar gerar ZIP on-demand
        if filekey == "zip" and rec.get("output_dir"):
            zip_path = _create_zip(rec["output_dir"], rec.get("title", "pacote"))
            update_transcription(tid, {"zip_path": zip_path})
            return send_file(zip_path, as_attachment=True)
        flash("Arquivo não encontrado.", "warning")
        return redirect(url_for("detail", tid=tid))

    return send_file(file_path, as_attachment=True)


# ══════════════════════════════════════════════════════════
#  ROTAS — AÇÕES
# ══════════════════════════════════════════════════════════

@app.route("/t/<int:tid>/delete", methods=["POST"])
def delete(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)

    # Remover arquivos
    output_dir = rec.get("output_dir")
    if output_dir and os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    input_path = rec.get("input_path")
    if input_path and os.path.isfile(input_path):
        os.remove(input_path)

    delete_transcription(tid)
    flash(f"Transcrição #{tid} deletada.", "info")
    return redirect(url_for("index"))


@app.route("/t/<int:tid>/zip", methods=["POST"])
def generate_zip(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)
    if rec.get("output_dir"):
        zip_path = _create_zip(rec["output_dir"], rec.get("title", "pacote"))
        update_transcription(tid, {"zip_path": zip_path})
        flash("ZIP gerado com sucesso!", "success")
    return redirect(url_for("detail", tid=tid))


@app.route("/t/<int:tid>/open", methods=["POST"])
def open_folder(tid):
    rec = get_transcription(tid)
    if not rec:
        abort(404)
    output_dir = rec.get("output_dir")
    if output_dir and os.path.isdir(output_dir):
        subprocess.Popen(["open", output_dir])
        flash("Pasta aberta no Finder.", "success")
    else:
        flash("Pasta não encontrada.", "warning")
    return redirect(url_for("detail", tid=tid))


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🎓 Transcritor de Aulas → NotebookLM PRO")
    print("="*60)

    if STARTUP_ISSUES:
        print("\n⚠️  AVISOS DE CONFIGURAÇÃO:")
        for issue in STARTUP_ISSUES:
            print(f"   ❌ {issue}")
        print()
    else:
        print("\n✅ Todas as dependências encontradas!\n")

    print(f"  📁 Data: {config.DATA_DIR}")
    print(f"  🤖 Modelo: {config.WHISPER_MODEL_PATH}")
    print(f"  🔊 Whisper: {config.WHISPER_BIN}")
    print(f"  🎬 FFmpeg: {config.FFMPEG_BIN}")
    print()

    app.run(debug=True, host="127.0.0.1", port=5001)
