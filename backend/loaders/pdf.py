"""PDF loader → common Document model."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.loaders.base import ChapterHeading, Document, Page

logger = logging.getLogger(__name__)


def load_pdf(filepath: str | Path) -> Document:
    """Parse a PDF file into the common Document model.

    Uses PyMuPDF (fitz) for text extraction.
    Chapter detection based on font size heuristics and TOC.
    """
    filepath = Path(filepath)

    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF is required for PDF loading: pip install PyMuPDF")

    doc = fitz.open(str(filepath))
    pages: list[Page] = []
    chapters: list[ChapterHeading] = []
    all_text: list[str] = []

    # Extract TOC for chapter structure
    toc = doc.get_toc(simple=False)
    chapter_order = 0
    chapter_page_map: dict[int, list[ChapterHeading]] = {}

    if toc:
        for level, title, page_num, *_ in toc:
            ch = ChapterHeading(
                title=title.strip(),
                level=min(level, 3),
                page=page_num,
                order=chapter_order,
            )
            chapters.append(ch)
            chapter_page_map.setdefault(page_num, []).append(ch)
            chapter_order += 1

    # Extract page text
    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        text = page.get_text(sort=True)
        pages.append(Page(number=page_num, text=text))
        all_text.append(text)

    doc.close()

    # Fallback chapter detection by font size if TOC is empty
    if not chapters:
        chapters = _detect_chapters_by_heuristics(pages)

    full_text = "\n".join(all_text)

    return Document(
        filename=filepath.name,
        file_type="pdf",
        pages=pages,
        chapters=chapters,
        full_text=full_text,
        char_count=len(full_text),
    )


def _detect_chapters_by_heuristics(pages: list[Page]) -> list[ChapterHeading]:
    """Simple heuristic: look for lines matching Chinese chapter patterns on early pages."""
    import re

    chapters: list[ChapterHeading] = []
    chapter_pattern = re.compile(
        r"^\s*(第[一二三四五六七八九十百千\d]+[章节]|Chapter\s*\d+|"
        r"[第]?\d+[\.、\s]+(?:概述|绪论|引言|总结|复习))"
    )

    for page in pages[:10]:
        for line in page.text.split("\n"):
            line = line.strip()
            if chapter_pattern.match(line) and len(line) < 60:
                chapters.append(ChapterHeading(
                    title=line,
                    level=1,
                    page=page.number,
                    order=len(chapters),
                ))

    return chapters
