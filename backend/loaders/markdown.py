"""Markdown loader → common Document model."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.loaders.base import ChapterHeading, Document

logger = logging.getLogger(__name__)


def load_markdown(filepath: str | Path) -> Document:
    """Parse a Markdown file into the common Document model.

    Chapter detection based on ATX headings (#).
    """
    filepath = Path(filepath)
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    chapters: list[ChapterHeading] = []

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    for i, line in enumerate(lines):
        m = heading_pattern.match(line.strip())
        if m:
            chapters.append(ChapterHeading(
                title=m.group(2).strip(),
                level=len(m.group(1)),
                page=i + 1,  # use line number as proxy for page
                order=len(chapters),
            ))

    return Document(
        filename=filepath.name,
        file_type="md",
        chapters=chapters,
        full_text=text,
        char_count=len(text),
    )
