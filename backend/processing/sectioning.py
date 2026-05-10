"""Chapter/section recognition from parsed documents."""

from __future__ import annotations

import uuid

from backend.loaders.base import Document
from backend.models.material import Material, Section


def recognize_sections(material: Material, document: Document) -> list[Section]:
    """Convert parsed document chapters into Section models.

    If the loader already detected chapters, use those.
    Otherwise, treat the whole document as one section.
    """
    if document.chapters:
        return _from_chapters(material, document)
    else:
        return [_single_section(material, document)]


def _from_chapters(material: Material, document: Document) -> list[Section]:
    sections: list[Section] = []
    textbook = document.filename.rsplit(".", 1)[0]

    for i, ch in enumerate(document.chapters):
        chapter_text = document.get_text_by_chapter(ch)
        sections.append(Section(
            id=f"sec_{uuid.uuid4().hex[:12]}",
            material_id=material.id,
            textbook=textbook,
            chapter=ch.title,
            order=ch.order,
            level=ch.level,
            page_start=ch.page,
            page_end=None,
            char_count=len(chapter_text),
            text=chapter_text,
        ))

    # Fill page_end from next section's page_start
    for i in range(len(sections) - 1):
        if sections[i + 1].page_start:
            sections[i].page_end = sections[i + 1].page_start

    return sections


def _single_section(material: Material, document: Document) -> Section:
    textbook = document.filename.rsplit(".", 1)[0]
    return Section(
        id=f"sec_{uuid.uuid4().hex[:12]}",
        material_id=material.id,
        textbook=textbook,
        chapter=textbook,
        order=0,
        level=1,
        page_start=1,
        page_end=len(document.pages) or None,
        char_count=document.char_count,
        text=document.full_text,
    )
