"""PDF loader → common Document model."""

from __future__ import annotations

import logging
from pathlib import Path
import re

from backend.core.config import settings
from backend.loaders.base import ChapterHeading, Document, Page

logger = logging.getLogger(__name__)


def load_pdf(filepath: str | Path) -> Document:
    """Parse a PDF file into the common Document model.

    The provider is controlled by PDF_PARSE_PROVIDER:
    - pymupdf: local text extraction only
    - mineru: MinerU Markdown extraction
    - auto: use PyMuPDF when text quality is acceptable, otherwise MinerU
    """
    filepath = Path(filepath)
    provider = settings.pdf_parse_provider.lower()
    if provider not in {"auto", "pymupdf", "mineru"}:
        raise ValueError(f"Unsupported PDF parse provider: {settings.pdf_parse_provider}")

    if provider == "mineru":
        return _load_pdf_with_mineru(filepath)

    document = _load_pdf_with_pymupdf(filepath)
    if provider == "pymupdf" or _is_text_quality_acceptable(document.full_text):
        return document

    try:
        logger.warning(
            "PyMuPDF text quality is low, falling back to MinerU",
            extra={
                "file_type": "pdf",
                "byte_size": filepath.stat().st_size,
                "char_count": document.char_count,
            },
        )
        return _load_pdf_with_mineru(filepath)
    except ImportError:
        logger.warning("MinerU not available, returning PyMuPDF result despite low quality")
        return document


def _load_pdf_with_pymupdf(filepath: Path) -> Document:
    """Parse a PDF file with PyMuPDF."""

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


def _load_pdf_with_mineru(filepath: Path) -> Document:
    try:
        from backend.loaders.mineru_client import parse_pdf_with_mineru
    except ImportError:
        raise ImportError(
            "mineru_client is not available. "
            "Ensure backend/loaders/mineru_client.py exists and is committed."
        )
    result = parse_pdf_with_mineru(filepath)
    return _load_mineru_markdown(result.markdown_path, filename=filepath.name)


def _load_mineru_markdown(filepath: str | Path, filename: str | None = None) -> Document:
    """Load MinerU Markdown and infer a textbook-friendly heading hierarchy."""
    filepath = Path(filepath)
    text = filepath.read_text(encoding="utf-8")
    chapters = _detect_mineru_headings(text)
    return Document(
        filename=filename or filepath.name,
        file_type="pdf",
        chapters=chapters,
        full_text=text,
        char_count=len(text),
    )


def _is_text_quality_acceptable(text: str) -> bool:
    """Reject mojibake-heavy PDF extraction before it pollutes KG/RAG."""
    stripped = "".join(ch for ch in text if not ch.isspace())
    if len(stripped) < 200:
        return False

    replacement_ratio = text.count("\ufffd") / max(len(text), 1)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    cjk_ratio = cjk_count / max(len(stripped), 1)
    return (
        replacement_ratio <= settings.pdf_max_replacement_ratio
        and cjk_ratio >= settings.pdf_min_cjk_ratio
    )


def _detect_mineru_headings(text: str) -> list[ChapterHeading]:
    heading_pattern = re.compile(r"^#{1,6}\s+(.+?)\s*$")
    chapters: list[ChapterHeading] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        match = heading_pattern.match(line.strip())
        if not match:
            continue
        raw_title = match.group(1).strip()
        if _looks_like_toc_heading(raw_title):
            continue
        title = _normalize_mineru_heading(raw_title)
        if not _is_teaching_heading(title):
            continue
        chapters.append(ChapterHeading(
            title=title,
            level=_infer_heading_level(title),
            page=line_no,
            order=len(chapters),
        ))

    return chapters


def _normalize_mineru_heading(title: str) -> str:
    title = re.sub(r"\s+", " ", title.replace("\u3000", " ")).strip()
    title = title.replace(" | ", " ")
    title = re.sub(r"\s*[.。·]+\s*\d+\s*$", "", title).strip()
    return title


def _looks_like_toc_heading(title: str) -> bool:
    compact = re.sub(r"\s+", " ", title.replace("\u3000", " ")).strip()
    return bool(re.match(r"^第[一二三四五六七八九十百千\d]+[章节].*(?:[.。]\s*)?\d+\s*$", compact))


def _is_teaching_heading(title: str) -> bool:
    if not title or len(title) > 80:
        return False
    front_matter = {"病理学", "Pathology", "版权所有，侵权必究！", "编 委 （以姓氏笔画为序）"}
    if title in front_matter:
        return False
    if re.match(r"^第[一二三四五六七八九十百千\d]+[章节].*\s+\d+$", title):
        return False
    if re.search(r"\s\d+\s*$", title) and not re.search(r"第[一二三四五六七八九十百千\d]+[章节]", title):
        return False
    return bool(
        re.match(r"^(绪\s*论|第[一二三四五六七八九十百千\d]+章\b)", title)
        or re.match(r"^第[一二三四五六七八九十百千\d]+节\b", title)
        or re.match(r"^[一二三四五六七八九十]+、", title)
        or re.match(r"^（[一二三四五六七八九十]+）", title)
    )


def _infer_heading_level(title: str) -> int:
    if re.match(r"^(绪\s*论|第[一二三四五六七八九十百千\d]+章\b)", title):
        return 1
    if re.match(r"^第[一二三四五六七八九十百千\d]+节\b", title):
        return 2
    return 3


def _detect_chapters_by_heuristics(pages: list[Page]) -> list[ChapterHeading]:
    """Simple heuristic: look for lines matching Chinese chapter patterns on early pages."""
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
