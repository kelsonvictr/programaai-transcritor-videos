"""
Módulo de banco de dados SQLite para o Transcritor.
"""
import sqlite3
import os
import json
from datetime import datetime
from config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    tags_json           TEXT DEFAULT '{}',
    original_filename   TEXT,
    input_path          TEXT,
    output_dir          TEXT,
    created_at          TEXT,
    started_at          TEXT,
    finished_at         TEXT,
    duration_seconds    REAL,
    status              TEXT DEFAULT 'PENDENTE',
    stage               TEXT DEFAULT '',
    percent             INTEGER DEFAULT 0,
    language            TEXT DEFAULT 'pt',
    use_vad             INTEGER DEFAULT 1,
    clean_text          INTEGER DEFAULT 1,
    add_timestamps      INTEGER DEFAULT 1,
    gen_notes           INTEGER DEFAULT 1,
    gen_chapters        INTEGER DEFAULT 1,
    gen_reels           INTEGER DEFAULT 1,
    model_name          TEXT DEFAULT 'medium',
    model_path          TEXT,
    transcript_txt_path TEXT,
    transcript_srt_path TEXT,
    transcript_vtt_path TEXT,
    chapters_md_path    TEXT,
    chapters_json_path  TEXT,
    notes_short_path    TEXT,
    notes_medium_path   TEXT,
    notes_detailed_path TEXT,
    prompts_txt_path    TEXT,
    reels_md_path       TEXT,
    reels_json_path     TEXT,
    index_json_path     TEXT,
    readme_path         TEXT,
    zip_path            TEXT,
    log_path            TEXT,
    error_message       TEXT
);
"""


def get_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.close()


def create_transcription(data: dict) -> int:
    conn = get_db()
    cols = list(data.keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    vals = [data[c] for c in cols]
    cur = conn.execute(
        f"INSERT INTO transcriptions ({col_names}) VALUES ({placeholders})", vals
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def update_transcription(tid: int, data: dict):
    conn = get_db()
    sets = ", ".join([f"{k} = ?" for k in data.keys()])
    vals = list(data.values()) + [tid]
    conn.execute(f"UPDATE transcriptions SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_transcription(tid: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM transcriptions WHERE id = ?", (tid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_transcriptions(status=None, tag=None, search=None):
    conn = get_db()
    q = "SELECT * FROM transcriptions WHERE 1=1"
    params = []
    if status:
        q += " AND status = ?"
        params.append(status)
    if tag:
        q += " AND tags_json LIKE ?"
        params.append(f"%{tag}%")
    if search:
        q += " AND (title LIKE ? OR original_filename LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_transcription(tid: int):
    conn = get_db()
    conn.execute("DELETE FROM transcriptions WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
