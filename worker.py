"""
Worker de processamento assíncrono para transcrições.
Executa em thread separada para não travar o Flask.
"""
import os
import re
import json
import shutil
import subprocess
import threading
import zipfile
from datetime import datetime
from math import floor

import config
from database import update_transcription, get_transcription


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def _log(log_path: str, msg: str):
    """Append ao arquivo de log."""
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _set(tid, **kw):
    update_transcription(tid, kw)


def _fmt_ts(seconds: float) -> str:
    """Segundos → HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ══════════════════════════════════════════════════════════
#  PARSE SRT
# ══════════════════════════════════════════════════════════

def _parse_srt(srt_path: str) -> list:
    """Retorna lista de dicts: {index, start, end, start_s, end_s, text}"""
    entries = []
    if not os.path.isfile(srt_path):
        return entries
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        time_match = re.match(
            r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})",
            lines[1].strip()
        )
        if not time_match:
            continue
        g = [int(x) for x in time_match.groups()]
        start_s = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
        end_s = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
        text = " ".join(lines[2:]).strip()
        entries.append({
            "index": idx,
            "start": lines[1].strip().split("-->")[0].strip(),
            "end": lines[1].strip().split("-->")[1].strip(),
            "start_s": start_s,
            "end_s": end_s,
            "text": text,
        })
    return entries


# ══════════════════════════════════════════════════════════
#  LIMPEZA LEVE
# ══════════════════════════════════════════════════════════

FILLER_WORDS = [
    r'\bné\b', r'\btá\b', r'\bhã\b', r'\bãh\b', r'\buhm\b',
    r'\buh\b', r'\beh\b', r'\bahm\b', r'\bham\b',
]

def _clean_text(text: str) -> str:
    """Remove muletas repetitivas de forma conservadora."""
    for pattern in FILLER_WORDS:
        # Remove apenas se isolada (não parte de palavra composta)
        text = re.sub(pattern + r'[,.]?\s*', ' ', text, flags=re.IGNORECASE)
    # Remover "tipo" apenas quando isolado (não "tipo int", "tipo float", etc.)
    text = re.sub(r'\btipo\b(?!\s+\w{2,})', ' ', text, flags=re.IGNORECASE)
    # Espaços duplos
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# ══════════════════════════════════════════════════════════
#  GERAR TRANSCRIPT.TXT COM TIMESTAMPS POR PARÁGRAFO
# ══════════════════════════════════════════════════════════

def _generate_transcript_txt(srt_entries, output_path, clean=True, add_ts=True,
                             group_size=None):
    group_size = group_size or config.DEFAULT_PARAGRAPH_GROUP_SIZE
    paragraphs = []
    for i in range(0, len(srt_entries), group_size):
        group = srt_entries[i:i+group_size]
        ts = _fmt_ts(group[0]["start_s"])
        texts = " ".join(e["text"] for e in group)
        if clean:
            texts = _clean_text(texts)
        if add_ts:
            paragraphs.append(f"[{ts}] {texts}")
        else:
            paragraphs.append(texts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(paragraphs))
    return paragraphs


# ══════════════════════════════════════════════════════════
#  CHAPTERING / CAPÍTULOS
# ══════════════════════════════════════════════════════════

TOPIC_SIGNALS = [
    "agora", "próximo", "vamos", "então", "resumindo",
    "exemplo", "na prática", "atenção", "importante",
    "primeiro", "segundo", "terceiro", "por fim", "conclusão",
    "outro ponto", "além disso", "voltando", "passando para",
    "seguinte", "continuando", "vamos falar", "o que é",
    "bom pessoal", "beleza", "certo", "ok então",
    "vamos ver", "olha só", "repare", "observe",
]

def _detect_chapters(srt_entries, window_seconds=None):
    """Detecta capítulos por heurística de palavras sinalizadoras e gaps."""
    window_seconds = window_seconds or config.DEFAULT_CHAPTER_WINDOW_SECONDS
    if not srt_entries:
        return []

    chapters = []
    total_duration = srt_entries[-1]["end_s"] if srt_entries else 0

    # Sempre adicionar capítulo de Introdução
    chapters.append({
        "start_s": 0,
        "start": "00:00:00",
        "title": "Introdução",
        "keywords": [],
    })

    last_chapter_time = 0.0
    for i, entry in enumerate(srt_entries):
        if entry["start_s"] - last_chapter_time < window_seconds:
            continue

        text_lower = entry["text"].lower()
        triggered_signal = None
        for signal in TOPIC_SIGNALS:
            if signal in text_lower:
                triggered_signal = signal
                break

        # Gaps longos (> 3s de silêncio entre legendas)
        gap = 0
        if i > 0:
            gap = entry["start_s"] - srt_entries[i-1]["end_s"]

        if triggered_signal or gap > 3.0:
            # Extrair keywords do contexto (próximas 5 legendas)
            context_texts = " ".join(
                srt_entries[j]["text"] for j in range(i, min(i+8, len(srt_entries)))
            )
            keywords = _extract_keywords(context_texts)
            title = _generate_chapter_title(context_texts, triggered_signal)
            chapters.append({
                "start_s": entry["start_s"],
                "start": _fmt_ts(entry["start_s"]),
                "title": title,
                "keywords": keywords[:5],
            })
            last_chapter_time = entry["start_s"]

    # Adicionar end_s aproximado a cada capítulo
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch["end_s"] = chapters[i+1]["start_s"]
        else:
            ch["end_s"] = total_duration
        ch["end"] = _fmt_ts(ch["end_s"])

    return chapters


def _extract_keywords(text: str, top_n=5) -> list:
    """Extrai termos-chave simples por frequência (TF leve)."""
    stopwords = {
        "a", "o", "e", "é", "de", "do", "da", "em", "um", "uma", "que", "se",
        "no", "na", "os", "as", "para", "com", "por", "mais", "mas", "como",
        "foi", "são", "não", "tem", "isso", "esse", "essa", "este", "esta",
        "eu", "ele", "ela", "nós", "você", "vocês", "gente", "aí", "aqui",
        "muito", "então", "porque", "quando", "onde", "já", "só", "vai",
        "vou", "vamos", "pode", "ser", "ter", "fazer", "né", "tipo", "tá",
        "lá", "assim", "também", "coisa", "coisas", "todo", "toda",
        "the", "is", "a", "an", "and", "or", "to", "in", "of", "for",
    }
    words = re.findall(r'\b[a-záàâãéêíóôõúüç]{3,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1
    sorted_w = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_w[:top_n]]


def _generate_chapter_title(context: str, signal: str = None) -> str:
    """Gera título simples para capítulo baseado no contexto."""
    # Pegar as primeiras palavras relevantes
    words = context.split()[:12]
    snippet = " ".join(words)
    # Limpar e capitalizar
    snippet = re.sub(r'[^\w\s\-áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]', '', snippet)
    if len(snippet) > 60:
        snippet = snippet[:60] + "…"
    return snippet.strip().capitalize() if snippet.strip() else "Continuação"


def _write_chapters(chapters, output_dir):
    """Escreve chapters.md e chapters.json"""
    md_path = os.path.join(output_dir, "chapters.md")
    json_path = os.path.join(output_dir, "chapters.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Capítulos da Aula\n\n")
        for ch in chapters:
            f.write(f"- **[{ch['start']}]** {ch['title']}\n")
            if ch.get("keywords"):
                f.write(f"  - Palavras-chave: {', '.join(ch['keywords'])}\n")
            f.write("\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

    return md_path, json_path


# ══════════════════════════════════════════════════════════
#  NOTES.MD (3 VERSÕES)
# ══════════════════════════════════════════════════════════

def _generate_notes(srt_entries, chapters, meta, output_dir):
    """Gera 3 versões de notas."""
    all_text = " ".join(e["text"] for e in srt_entries)
    keywords = _extract_keywords(all_text, top_n=20)
    glossary_terms = keywords[:15]

    header = f"""---
Aula: {meta.get('title', 'Sem título')}
Tags: {meta.get('tags', '')}
Data: {meta.get('created_at', '')}
Duração: {meta.get('duration', 'N/A')}
Modelo: {meta.get('model_name', 'medium')}
VAD: {'Sim' if meta.get('use_vad') else 'Não'}
---

> 💡 **Como usar no NotebookLM:** Importe este arquivo junto com `transcript.txt` e `chapters.md`. Use os prompts de `notebooklm_prompts.txt` para gerar conteúdo.

"""

    prompts_section = """
## 🎯 Prompts Recomendados para NotebookLM

1. "Resuma esta aula em 10 tópicos com 1 linha por tópico."
2. "Crie flashcards dos conceitos principais."
3. "Gere exercícios práticos sobre o conteúdo."
"""

    questions_section = """
## ❓ Perguntas que o Aluno Deve Conseguir Responder

"""
    for i, kw in enumerate(keywords[:8], 1):
        questions_section += f"{i}. O que é/como funciona **{kw}**?\n"

    # ── SHORT ─────────────────────────────────────────────
    short_path = os.path.join(output_dir, "notes_short.md")
    with open(short_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("# 📝 Notas da Aula (Resumo)\n\n")
        f.write("## Pontos Principais\n\n")

        # Bullets dos capítulos
        for ch in chapters[:12]:
            f.write(f"- **[{ch['start']}]** {ch['title']}\n")

        f.write("\n## 📖 Glossário\n\n")
        for term in glossary_terms[:5]:
            f.write(f"- **{term.capitalize()}**: _definição a partir do contexto da aula_\n")

        f.write("\n## 💡 Exemplos Citados\n\n")
        f.write("1. _(extrair do conteúdo via NotebookLM)_\n")
        f.write("2. _(extrair do conteúdo via NotebookLM)_\n")
        f.write("3. _(extrair do conteúdo via NotebookLM)_\n")

        f.write(prompts_section)
        f.write(questions_section)

    # ── MEDIUM ────────────────────────────────────────────
    medium_path = os.path.join(output_dir, "notes_medium.md")
    with open(medium_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("# 📝 Notas da Aula (Completa)\n\n")

        f.write("## 📋 Tópicos e Capítulos\n\n")
        for ch in chapters:
            f.write(f"### [{ch['start']}] {ch['title']}\n")
            if ch.get("keywords"):
                f.write(f"_Termos: {', '.join(ch['keywords'])}_\n")
            f.write("\n")

        f.write("## ✅ Checklist do que foi ensinado\n\n")
        for ch in chapters:
            f.write(f"- [ ] {ch['title']}\n")

        f.write("\n## 📖 Glossário\n\n")
        for term in glossary_terms[:10]:
            f.write(f"- **{term.capitalize()}**: _definição a partir do contexto da aula_\n")

        f.write("\n## 🧠 Conceitos-Chave\n\n")
        for kw in keywords[:10]:
            f.write(f"- {kw.capitalize()}\n")

        f.write("\n## 📝 Sugestões de Exercícios\n\n")
        for i in range(1, 6):
            f.write(f"{i}. Exercício sobre os conceitos da aula _(gerar via NotebookLM)_\n")

        f.write(prompts_section)
        f.write(questions_section)

    # ── DETAILED ──────────────────────────────────────────
    detailed_path = os.path.join(output_dir, "notes_detailed.md")
    with open(detailed_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("# 📝 Notas da Aula (Apostila Detalhada)\n\n")

        f.write("## 1. Introdução\n\n")
        f.write(f"Esta apostila cobre os principais tópicos da aula **{meta.get('title', '')}**.\n\n")

        f.write("## 2. Conteúdo por Seção\n\n")
        for i, ch in enumerate(chapters, 1):
            f.write(f"### 2.{i}. [{ch['start']}] {ch['title']}\n\n")
            # Extrair texto do intervalo deste capítulo
            start_s = ch.get("start_s", 0)
            end_s = ch.get("end_s", 9999999)
            section_texts = [e["text"] for e in srt_entries
                           if start_s <= e["start_s"] < end_s]
            preview = " ".join(section_texts[:20])
            if len(preview) > 500:
                preview = preview[:500] + "…"
            f.write(f"> {preview}\n\n")
            if ch.get("keywords"):
                f.write(f"**Termos-chave:** {', '.join(ch['keywords'])}\n\n")

        f.write("## 3. Glossário Completo\n\n")
        for term in glossary_terms:
            f.write(f"- **{term.capitalize()}**: _consulte o contexto da aula para definição precisa_\n")

        f.write("\n## 4. Conceitos-Chave\n\n")
        for kw in keywords[:15]:
            f.write(f"- {kw.capitalize()}\n")

        f.write("\n## 5. ✅ Checklist de Aprendizado\n\n")
        for ch in chapters:
            f.write(f"- [ ] {ch['title']}\n")

        f.write("\n## 6. ⚠️ Armadilhas Comuns\n\n")
        f.write("- _(gerar via NotebookLM com o prompt: \"Liste armadilhas/erros comuns\")_\n")

        f.write("\n## 7. ❓ FAQ\n\n")
        f.write("- _(gerar via NotebookLM com o prompt: \"Extraia 10 dúvidas comuns\")_\n")

        f.write("\n## 8. 📝 Sugestões de Exercícios\n\n")
        for i in range(1, 11):
            difficulty = "Fácil" if i <= 3 else ("Médio" if i <= 6 else "Difícil")
            f.write(f"{i}. [{difficulty}] Exercício sobre os conceitos da aula\n")

        f.write(prompts_section)
        f.write(questions_section)

    return short_path, medium_path, detailed_path


# ══════════════════════════════════════════════════════════
#  REELS CUTS
# ══════════════════════════════════════════════════════════

REELS_SIGNALS = [
    "atenção", "importante", "cai muito", "erro comum", "macete",
    "dica", "cuidado", "truque", "segredo", "essencial",
    "na prática", "exemplo", "olha só", "repare", "observe",
    "nunca", "sempre", "principal", "fundamental", "chave",
]

def _detect_reels_cuts(srt_entries, max_cuts=None):
    """Detecta trechos bons para Reels (30s/45s/60s)."""
    max_cuts = max_cuts or config.DEFAULT_REELS_CUT_COUNT
    if not srt_entries:
        return []

    candidates = []
    for i, entry in enumerate(srt_entries):
        text_lower = entry["text"].lower()
        score = 0
        for signal in REELS_SIGNALS:
            if signal in text_lower:
                score += 2

        # Trechos com frases mais curtas e declarativas ganham pontos
        if len(entry["text"].split()) < 20:
            score += 1

        if score > 0:
            candidates.append((i, score, entry))

    # Ordenar por score
    candidates.sort(key=lambda x: -x[1])

    cuts = []
    used_times = set()

    for idx, score, entry in candidates:
        if len(cuts) >= max_cuts:
            break

        start_s = entry["start_s"]
        # Evitar cortes muito próximos (mínimo 60s de distância)
        too_close = False
        for used_t in used_times:
            if abs(start_s - used_t) < 60:
                too_close = True
                break
        if too_close:
            continue

        # Determinar duração do corte (30s, 45s ou 60s)
        # Verificar quantas legendas cabem
        context_entries = [e for e in srt_entries
                         if start_s <= e["start_s"] < start_s + 60]
        text_len = sum(len(e["text"]) for e in context_entries)

        if text_len < 100:
            duration = 30
        elif text_len < 200:
            duration = 45
        else:
            duration = 60

        end_s = min(start_s + duration,
                    srt_entries[-1]["end_s"] if srt_entries else start_s + duration)

        # Juntar texto do corte para gerar hook
        cut_texts = [e["text"] for e in srt_entries
                    if start_s <= e["start_s"] < end_s]
        full_text = " ".join(cut_texts)
        hook = full_text[:80] + ("…" if len(full_text) > 80 else "")

        cuts.append({
            "number": len(cuts) + 1,
            "start_s": start_s,
            "end_s": end_s,
            "start": _fmt_ts(start_s),
            "end": _fmt_ts(end_s),
            "duration": duration,
            "title": f"Corte {len(cuts)+1}: {entry['text'][:50]}",
            "hook": hook,
            "reason": f"Contém termo de destaque relevante (score: {score})",
            "suggested_caption": entry["text"][:100],
        })
        used_times.add(start_s)

    return cuts


def _write_reels(cuts, output_dir):
    """Escreve reels_cuts.md e reels.json"""
    md_path = os.path.join(output_dir, "reels_cuts.md")
    json_path = os.path.join(output_dir, "reels.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 🎬 Cortes para Reels\n\n")
        f.write(f"Total de sugestões: {len(cuts)}\n\n")
        for cut in cuts:
            f.write(f"## Corte {cut['number']}\n\n")
            f.write(f"- **Início:** {cut['start']}\n")
            f.write(f"- **Fim:** {cut['end']}\n")
            f.write(f"- **Duração:** {cut['duration']}s\n")
            f.write(f"- **Título:** {cut['title']}\n")
            f.write(f"- **Hook:** {cut['hook']}\n")
            f.write(f"- **Por que funciona:** {cut['reason']}\n")
            f.write(f"- **Legenda sugerida:** {cut['suggested_caption']}\n\n")
            f.write("---\n\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cuts, f, ensure_ascii=False, indent=2)

    return md_path, json_path


# ══════════════════════════════════════════════════════════
#  PROMPTS NOTEBOOKLM
# ══════════════════════════════════════════════════════════

NOTEBOOKLM_PROMPTS = [
    ("📋 Resumo em 10 tópicos",
     "Resuma esta aula em 10 tópicos principais. Para cada tópico, escreva 1 linha clara e objetiva."),
    ("📖 Apostila para iniciantes",
     "Crie uma apostila completa para iniciantes com base nesta aula. Inclua explicações passo a passo, exemplos práticos em Python e 5 exercícios no fim com gabarito."),
    ("🃏 Flashcards (20)",
     "Crie 20 flashcards no formato Pergunta / Resposta, focados nos conceitos-chave desta aula. As respostas devem ser curtas e diretas."),
    ("📝 Exercícios (15)",
     "Gere 15 exercícios sobre o conteúdo desta aula: 5 fáceis, 5 médios e 5 difíceis. Inclua o gabarito ao final."),
    ("📊 Slides (12)",
     "Transforme o conteúdo desta aula em 12 slides. Cada slide deve ter: título, 3 bullet points e 1 exemplo. Formato: SLIDE 1: ..."),
    ("❓ Dúvidas comuns (10)",
     "Extraia 10 dúvidas comuns que alunos teriam sobre esta aula e responda cada uma de forma simples e direta."),
    ("📅 Plano de revisão (7 dias)",
     "Crie um plano de revisão de 7 dias com base nesta aula. Cada dia deve ter tarefas específicas, curtas e práticas."),
    ("⚠️ Armadilhas e erros comuns",
     "Liste as armadilhas e erros comuns relacionados ao conteúdo desta aula. Explique cada um e como evitar."),
    ("🎯 Simulado (10 questões)",
     "Gere um simulado de 10 questões de múltipla escolha (A-D) sobre o conteúdo desta aula. Inclua gabarito ao final."),
    ("🎬 Cortes para Reels",
     "Sugira 10 cortes de até 60 segundos desta aula que funcionariam bem como Reels no Instagram. Para cada corte, inclua: timestamp de início e fim, título chamativo e por que funciona."),
    ("🗺️ Mapa mental",
     "Crie um mapa mental textual (com indentação) do conteúdo desta aula, mostrando hierarquia de conceitos."),
    ("📚 Indicações de estudo",
     "Com base no conteúdo desta aula, sugira 5 livros, 5 artigos/posts e 5 vídeos complementares para aprofundamento."),
]


def _write_prompts(output_dir, title=""):
    prompts_path = os.path.join(output_dir, "notebooklm_prompts.txt")
    with open(prompts_path, "w", encoding="utf-8") as f:
        f.write(f"# Prompts para NotebookLM — {title}\n")
        f.write(f"# Copie e cole no NotebookLM após importar os arquivos da aula.\n\n")
        for i, (label, prompt) in enumerate(NOTEBOOKLM_PROMPTS, 1):
            f.write(f"{'='*60}\n")
            f.write(f"PROMPT {i}: {label}\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"{prompt}\n\n")
    return prompts_path


# ══════════════════════════════════════════════════════════
#  INDEX.JSON + README
# ══════════════════════════════════════════════════════════

def _write_index(output_dir, meta, chapters, cuts):
    index_path = os.path.join(output_dir, "index.json")
    data = {
        "title": meta.get("title", ""),
        "tags": meta.get("tags", ""),
        "created_at": meta.get("created_at", ""),
        "duration_seconds": meta.get("duration_seconds", 0),
        "duration_formatted": meta.get("duration", "N/A"),
        "language": meta.get("language", "pt"),
        "model": meta.get("model_name", "medium"),
        "use_vad": meta.get("use_vad", True),
        "files": {
            "transcript_txt": "transcript.txt",
            "transcript_srt": "transcript.srt",
            "transcript_vtt": "transcript.vtt",
            "chapters_md": "chapters.md",
            "chapters_json": "chapters.json",
            "notes_short": "notes_short.md",
            "notes_medium": "notes_medium.md",
            "notes_detailed": "notes_detailed.md",
            "prompts": "notebooklm_prompts.txt",
            "reels_md": "reels_cuts.md",
            "reels_json": "reels.json",
        },
        "chapters_count": len(chapters),
        "reels_cuts_count": len(cuts),
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return index_path


def _write_readme(output_dir, meta):
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# 📦 Pacote NotebookLM — {meta.get('title', 'Aula')}\n\n")
        f.write(f"**Data:** {meta.get('created_at', '')}\n")
        f.write(f"**Duração:** {meta.get('duration', 'N/A')}\n")
        f.write(f"**Modelo:** {meta.get('model_name', 'medium')}\n\n")
        f.write("## 📂 Arquivos do Pacote\n\n")
        f.write("| Arquivo | Descrição |\n")
        f.write("|---------|----------|\n")
        f.write("| `transcript.txt` | Transcrição limpa com timestamps por parágrafo |\n")
        f.write("| `transcript.srt` | Legendas SRT |\n")
        f.write("| `transcript.vtt` | Legendas WebVTT |\n")
        f.write("| `chapters.md` | Capítulos detectados com timestamps |\n")
        f.write("| `notes_short.md` | Notas resumidas |\n")
        f.write("| `notes_medium.md` | Notas completas |\n")
        f.write("| `notes_detailed.md` | Apostila detalhada |\n")
        f.write("| `notebooklm_prompts.txt` | Prompts prontos para copiar |\n")
        f.write("| `reels_cuts.md` | Sugestões de cortes para Reels |\n")
        f.write("| `index.json` | Metadados para automação |\n\n")
        f.write("## 🚀 Como Importar no NotebookLM\n\n")
        f.write("1. Acesse [notebooklm.google.com](https://notebooklm.google.com)\n")
        f.write("2. Crie um novo Notebook\n")
        f.write("3. Importe os seguintes arquivos (recomendado):\n")
        f.write("   - `transcript.txt` (fonte principal)\n")
        f.write("   - `notes_medium.md` (notas organizadas)\n")
        f.write("   - `chapters.md` (estrutura de tópicos)\n")
        f.write("4. Use os prompts de `notebooklm_prompts.txt` para gerar conteúdo\n\n")
        f.write("## 💡 Dicas\n\n")
        f.write("- O NotebookLM funciona melhor com **blocos curtos** de texto\n")
        f.write("- Importe `notes_detailed.md` se quiser análise mais profunda\n")
        f.write("- Use `reels_cuts.md` para planejar conteúdo de redes sociais\n")
    return readme_path


# ══════════════════════════════════════════════════════════
#  ZIP DO PACOTE
# ══════════════════════════════════════════════════════════

PACKAGE_FILES = [
    "transcript.txt", "transcript.srt", "transcript.vtt",
    "chapters.md", "chapters.json",
    "notes_short.md", "notes_medium.md", "notes_detailed.md",
    "notebooklm_prompts.txt",
    "reels_cuts.md", "reels.json",
    "index.json", "README.md",
]

def _create_zip(output_dir, title="pacote"):
    zip_path = os.path.join(output_dir, "package.zip")
    safe_title = re.sub(r'[^\w\-]', '_', title)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in PACKAGE_FILES:
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, f"{safe_title}/{fname}")
    return zip_path


# ══════════════════════════════════════════════════════════
#  WORKER PRINCIPAL
# ══════════════════════════════════════════════════════════

def start_worker(tid: int):
    """Inicia processamento em thread separada."""
    t = threading.Thread(target=_run_pipeline, args=(tid,), daemon=True)
    t.start()


def _run_pipeline(tid: int):
    """Pipeline completo de processamento."""
    rec = get_transcription(tid)
    if not rec:
        return

    output_dir = rec["output_dir"]
    input_path = rec["input_path"]
    log_path = os.path.join(output_dir, "logs.txt")
    model_path = rec["model_path"] or config.MODEL_PATH
    language = rec["language"] or config.DEFAULT_LANGUAGE
    use_vad = bool(rec["use_vad"])
    clean = bool(rec["clean_text"])
    add_ts = bool(rec["add_timestamps"])
    gen_notes = bool(rec["gen_notes"])
    gen_chapters = bool(rec["gen_chapters"])
    gen_reels = bool(rec["gen_reels"])

    os.makedirs(output_dir, exist_ok=True)

    _set(tid, status="PROCESSANDO", stage="PROBE", percent=5,
         started_at=datetime.now().isoformat(), log_path=log_path)
    _log(log_path, "Iniciando pipeline de processamento…")

    try:
        # ── PROBE ─────────────────────────────────────────
        _log(log_path, "ETAPA: PROBE — obtendo duração com ffprobe")
        duration = _probe_duration(input_path, log_path)
        dur_fmt = _fmt_ts(duration) if duration else "N/A"
        _set(tid, duration_seconds=duration, percent=10)
        _log(log_path, f"Duração detectada: {dur_fmt} ({duration:.1f}s)")

        # ── EXTRAI AUDIO ──────────────────────────────────
        _set(tid, stage="EXTRAI_AUDIO", percent=15)
        _log(log_path, "ETAPA: EXTRAI_AUDIO — convertendo para WAV 16kHz mono")
        wav_path = os.path.join(output_dir, "audio.wav")
        _extract_audio(input_path, wav_path, log_path)
        _log(log_path, "Áudio extraído com sucesso.")

        # ── TRANSCREVER ───────────────────────────────────
        _set(tid, stage="TRANSCRIBE", percent=25)
        _log(log_path, "ETAPA: TRANSCRIBE — executando whisper-cli")
        _transcribe(wav_path, model_path, language, use_vad, output_dir, log_path)
        _set(tid, percent=60)
        _log(log_path, "Transcrição concluída.")

        # Padronizar nomes dos arquivos gerados pelo whisper
        _standardize_whisper_outputs(output_dir, log_path)

        srt_path = os.path.join(output_dir, "transcript.srt")
        vtt_path = os.path.join(output_dir, "transcript.vtt")
        txt_path = os.path.join(output_dir, "transcript.txt")

        _set(tid, transcript_srt_path=srt_path, transcript_vtt_path=vtt_path)

        # ── PÓS-PROCESSAMENTO ────────────────────────────
        _set(tid, stage="POST_PROCESS", percent=65)
        _log(log_path, "ETAPA: POST_PROCESS — gerando transcript.txt com timestamps")
        srt_entries = _parse_srt(srt_path)
        _generate_transcript_txt(srt_entries, txt_path, clean=clean, add_ts=add_ts)
        _set(tid, transcript_txt_path=txt_path)
        _log(log_path, f"Transcript.txt gerado: {len(srt_entries)} legendas processadas.")

        # ── CHAPTERING ────────────────────────────────────
        chapters = []
        if gen_chapters:
            _set(tid, stage="CHAPTERING", percent=70)
            _log(log_path, "ETAPA: CHAPTERING — detectando capítulos")
            chapters = _detect_chapters(srt_entries)
            ch_md, ch_json = _write_chapters(chapters, output_dir)
            _set(tid, chapters_md_path=ch_md, chapters_json_path=ch_json)
            _log(log_path, f"Capítulos detectados: {len(chapters)}")

        # ── NOTES ─────────────────────────────────────────
        if gen_notes:
            _set(tid, stage="NOTES", percent=75)
            _log(log_path, "ETAPA: NOTES — gerando 3 versões de notas")
            meta = {
                "title": rec["title"],
                "tags": rec.get("tags_json", ""),
                "created_at": rec["created_at"],
                "duration": dur_fmt,
                "duration_seconds": duration,
                "model_name": rec["model_name"],
                "use_vad": use_vad,
                "language": language,
            }
            ns, nm, nd = _generate_notes(srt_entries, chapters, meta, output_dir)
            _set(tid, notes_short_path=ns, notes_medium_path=nm, notes_detailed_path=nd)
            _log(log_path, "Notas geradas (short, medium, detailed).")

        # ── REELS ─────────────────────────────────────────
        cuts = []
        if gen_reels:
            _set(tid, stage="REELS", percent=80)
            _log(log_path, "ETAPA: REELS — detectando cortes para Reels")
            cuts = _detect_reels_cuts(srt_entries)
            r_md, r_json = _write_reels(cuts, output_dir)
            _set(tid, reels_md_path=r_md, reels_json_path=r_json)
            _log(log_path, f"Cortes para Reels detectados: {len(cuts)}")

        # ── PACKAGE ───────────────────────────────────────
        _set(tid, stage="PACKAGE", percent=85)
        _log(log_path, "ETAPA: PACKAGE — gerando prompts, index, README e ZIP")

        meta_for_index = {
            "title": rec["title"],
            "tags": rec.get("tags_json", ""),
            "created_at": rec["created_at"],
            "duration_seconds": duration,
            "duration": dur_fmt,
            "language": language,
            "model_name": rec["model_name"],
            "use_vad": use_vad,
        }

        prompts_path = _write_prompts(output_dir, rec["title"])
        index_path = _write_index(output_dir, meta_for_index, chapters, cuts)
        readme_path = _write_readme(output_dir, meta_for_index)

        _set(tid, prompts_txt_path=prompts_path, index_json_path=index_path,
             readme_path=readme_path)

        zip_path = _create_zip(output_dir, rec["title"])
        _set(tid, zip_path=zip_path, percent=95)
        _log(log_path, "ZIP do pacote gerado.")

        # ── DONE ──────────────────────────────────────────
        _set(tid, status="CONCLUÍDA", stage="DONE", percent=100,
             finished_at=datetime.now().isoformat())
        _log(log_path, "✅ Pipeline concluído com sucesso!")

    except Exception as e:
        _set(tid, status="ERRO", stage="ERRO", error_message=str(e))
        _log(log_path, f"❌ ERRO: {str(e)}")
        import traceback
        _log(log_path, traceback.format_exc())


# ══════════════════════════════════════════════════════════
#  FUNÇÕES DE EXECUÇÃO DE COMANDOS
# ══════════════════════════════════════════════════════════

def _probe_duration(input_path, log_path):
    cmd = [
        config.FFPROBE_BIN, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path
    ]
    _log(log_path, f"CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    _log(log_path, f"stdout: {result.stdout.strip()}")
    if result.stderr:
        _log(log_path, f"stderr: {result.stderr.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe falhou: {result.stderr}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"ffprobe retornou valor inválido: {result.stdout}")


def _extract_audio(input_path, wav_path, log_path):
    cmd = [
        config.FFMPEG_BIN, "-y", "-i", input_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        wav_path
    ]
    _log(log_path, f"CMD: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.stderr:
        _log(log_path, f"ffmpeg stderr (últimas linhas):\n{result.stderr[-500:]}")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou (code {result.returncode})")


def _transcribe(wav_path, model_path, language, use_vad, output_dir, log_path):
    cmd = [
        config.WHISPER_BIN,
        "-m", model_path,
        "-f", wav_path,
        "-l", language,
        "-osrt", "-ovtt", "-otxt",
        "-t", "8",  # Usar 8 threads para paralelizar
        "-p", "1",  # Processar 1 vez (sem repetições)
    ]
    
    # Desabilitar GPU se configurado (evita crash do Metal no Apple Silicon)
    if not config.WHISPER_USE_GPU:
        cmd.append("--no-gpu")
    
    # Nota: VAD requer modelo separado, whisper já faz detecção de voz internamente
    # Se use_vad=True no futuro, adicionar: --vad-model <path>

    _log(log_path, f"CMD: {' '.join(cmd)}")
    _log(log_path, "⏳ Processando... (pode levar vários minutos)")
    _log(log_path, "💡 Dica: Para vídeos longos, considere usar o modelo 'small' ou 'base'")
    
    # Executar com output em tempo real
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=output_dir,
        bufsize=1,
        universal_newlines=True
    )
    
    # Capturar e logar output em tempo real
    output_lines = []
    for line in process.stdout:
        output_lines.append(line)
        # Logar progresso a cada 50 linhas
        if len(output_lines) % 50 == 0:
            _log(log_path, f"[whisper] Processando... ({len(output_lines)} linhas)")
    
    process.wait(timeout=7200)  # 2h max
    
    full_output = ''.join(output_lines)
    _log(log_path, f"whisper output (últimas linhas):\n{full_output[-1000:]}")
    
    if process.returncode != 0:
        raise RuntimeError(f"whisper-cli falhou (code {process.returncode}): {full_output[-500:]}")


def _standardize_whisper_outputs(output_dir, log_path):
    """Renomeia os arquivos gerados pelo whisper para nomes padrão."""
    _log(log_path, "Padronizando nomes dos arquivos do whisper…")
    mappings = {
        ".srt": "transcript.srt",
        ".vtt": "transcript.vtt",
        ".txt": "transcript.txt",
    }

    for fname in os.listdir(output_dir):
        for ext, target in mappings.items():
            target_path = os.path.join(output_dir, target)
            if fname.endswith(ext) and fname != target and "audio" in fname.lower():
                src = os.path.join(output_dir, fname)
                if not os.path.exists(target_path):
                    shutil.copy2(src, target_path)
                    _log(log_path, f"  {fname} → {target}")
                break

    # Verificar se transcript.txt foi gerado (senão, criar do SRT)
    txt_path = os.path.join(output_dir, "transcript.txt")
    srt_path = os.path.join(output_dir, "transcript.srt")
    if not os.path.exists(txt_path) and os.path.exists(srt_path):
        _log(log_path, "transcript.txt não encontrado, será gerado do SRT no pós-processamento.")

    # Procurar por qualquer .srt/.vtt/.txt gerado se ainda não mapeou
    for fname in os.listdir(output_dir):
        for ext, target in mappings.items():
            target_path = os.path.join(output_dir, target)
            if fname.endswith(ext) and fname != target and not os.path.exists(target_path):
                src = os.path.join(output_dir, fname)
                shutil.copy2(src, target_path)
                _log(log_path, f"  {fname} → {target} (fallback)")
