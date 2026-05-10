"""Section-scoped chunking with sentence-boundary splitting."""

from __future__ import annotations

import re
import uuid

from backend.models.material import Chunk, Section

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


def chunk_sections(
    sections: list[Section],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split each section into overlapping chunks.

    Chunks respect sentence boundaries and never cross chapter boundaries.
    """
    chunks: list[Chunk] = []

    for section in sections:
        section_chunks = _chunk_text(
            text=section.text,
            section_id=section.id,
            textbook=section.textbook,
            chapter=section.chapter,
            page_start=section.page_start,
            page_end=section.page_end,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunks.extend(section_chunks)

    return chunks


def _chunk_text(
    text: str,
    section_id: str,
    textbook: str,
    chapter: str,
    page_start: int | None,
    page_end: int | None,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Split a single section's text into chunks at sentence boundaries."""
    sentences = _split_sentences(text)
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    chunk_index = 0

    for sentence in sentences:
        sent_len = len(sentence)

        if current_len + sent_len > chunk_size and current:
            # Flush current chunk
            chunk_text = "".join(current)
            chunks.append(Chunk(
                id=f"chk_{uuid.uuid4().hex[:12]}",
                section_id=section_id,
                textbook=textbook,
                chapter=chapter,
                page_start=page_start,
                page_end=page_end,
                text=chunk_text,
                char_count=len(chunk_text),
                chunk_index=chunk_index,
            ))
            chunk_index += 1

            # Keep overlap: retain last N chars worth of sentences
            overlap_text = ""
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= chunk_overlap:
                    overlap_text = s + overlap_text
                    overlap_len += len(s)
                else:
                    break
            current = [overlap_text] if overlap_text else []
            current_len = len(overlap_text)

        current.append(sentence)
        current_len += sent_len

    # Don't forget the last chunk
    if current:
        chunk_text = "".join(current)
        chunks.append(Chunk(
            id=f"chk_{uuid.uuid4().hex[:12]}",
            section_id=section_id,
            textbook=textbook,
            chapter=chapter,
            page_start=page_start,
            page_end=page_end,
            text=chunk_text,
            char_count=len(chunk_text),
            chunk_index=chunk_index,
        ))

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split Chinese/English text at sentence boundaries."""
    # Reattach the delimiter
    result: list[str] = []
    delim_positions = [m.start() for m in re.finditer(r"[。！？.!?\n]", text)]
    delim_positions.append(len(text))

    start = 0
    for end in delim_positions:
        if end < len(text) and text[end] in "。！？.!?\n":
            result.append(text[start:end + 1])
            start = end + 1
        elif end >= len(text):
            if start < len(text):
                result.append(text[start:])
        else:
            result.append(text[start:end])
            start = end

    # Cleanup: merge single-char splits
    merged: list[str] = []
    buf = ""
    for s in result:
        s = s.strip()
        if not s:
            continue
        buf += s
        if s[-1] in "。！？.!?\n":
            merged.append(buf)
            buf = ""
    if buf:
        merged.append(buf)

    return merged if merged else [text]
