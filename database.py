"""
Módulo de banco de dados SQLite para o Transcritor — Versão Rápida.
"""
import sqlite3
import os
from config import DB_PATH, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
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
    model_path          TEXT,
    transcript_txt      TEXT,
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
    # Migrar tabela antiga se existir (adicionar coluna transcript_txt)
    try:
        conn.execute("ALTER TABLE transcriptions ADD COLUMN transcript_txt TEXT")
    except sqlite3.OperationalError:
        pass  # coluna já existe
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


def list_transcriptions(search=None):
    conn = get_db()
    q = "SELECT * FROM transcriptions WHERE 1=1"
    params = []
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
