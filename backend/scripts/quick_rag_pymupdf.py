"""Create a fast PyMuPDF + lexical RAG corpus for time-critical demos."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import fitz

from backend.core.config import settings


PROJECT_ID = "proj_rag_fast"
PROJECT_NAME = "PyMuPDF RAG Fast"
TEXTBOOKS_DIR = Path(settings.textbooks_dir or r"E:\Desktop\大学\比赛\浙大AI全栈极速黑客松！\textbooks")
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def main() -> None:
    project_dir = Path(settings.data_root) / "projects" / PROJECT_ID
    chunks_dir = project_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    project = {
        "id": PROJECT_ID,
        "name": PROJECT_NAME,
        "status": "draft",
        "compressionRatio": 0,
        "createdAt": datetime.utcnow().isoformat(),
    }
    (project_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    output = chunks_dir / "rag_chunks.jsonl"
    total_chunks = 0
    total_chars = 0
    with open(output, "w", encoding="utf-8") as f:
        for pdf in sorted(TEXTBOOKS_DIR.glob("*.pdf")):
            book_chunks, book_chars = _write_pdf_chunks(pdf, f)
            total_chunks += book_chunks
            total_chars += book_chars
            print(f"{pdf.name}: chunks={book_chunks} chars={book_chars}", flush=True)

    print(f"project_id={PROJECT_ID}")
    print(f"chunks={total_chunks} chars={total_chars}")


def _write_pdf_chunks(pdf: Path, f) -> tuple[int, int]:
    doc = fitz.open(str(pdf))
    textbook = pdf.stem
    chunk_count = 0
    char_count = 0
    try:
        for page_index, page in enumerate(doc, start=1):
            text = _clean_text(page.get_text(sort=True))
            if len(text) < 80:
                continue
            char_count += len(text)
            chapter = _guess_chapter(text, textbook)
            for chunk_index, chunk in enumerate(_sliding_chunks(text)):
                chunk_id = f"{_safe_id(textbook)}_p{page_index:04d}_{chunk_index:02d}"
                f.write(json.dumps({
                    "id": chunk_id,
                    "text": chunk,
                    "metadata": {
                        "chunk_id": chunk_id,
                        "textbook": textbook,
                        "chapter": chapter,
                        "page_start": page_index,
                        "page_end": page_index,
                    },
                }, ensure_ascii=False) + "\n")
                chunk_count += 1
    finally:
        doc.close()
    return chunk_count, char_count


def _clean_text(text: str) -> str:
    text = text.replace("\ufffd", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _guess_chapter(text: str, fallback: str) -> str:
    for line in text.splitlines()[:12]:
        line = line.strip()
        if re.match(r"^(绪\s*论|第[一二三四五六七八九十百千\d]+章)", line):
            return line[:80]
    return fallback


def _sliding_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value)


if __name__ == "__main__":
    main()
