"""Common document model shared by all format loaders."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChapterHeading:
    title: str
    level: int
    page: int | None = None
    order: int = 0


@dataclass
class Page:
    number: int
    text: str
    char_count: int = 0

    def __post_init__(self):
        if not self.char_count:
            self.char_count = len(self.text)


@dataclass
class Document:
    """Common model produced by all format loaders."""

    filename: str
    file_type: str  # pdf, md, docx, xlsx
    pages: list[Page] = field(default_factory=list)
    chapters: list[ChapterHeading] = field(default_factory=list)
    full_text: str = ""
    char_count: int = 0

    def __post_init__(self):
        if not self.char_count and self.full_text:
            self.char_count = len(self.full_text)

    def get_text_by_chapter(self, chapter: ChapterHeading) -> str:
        """Extract text belonging to a specific chapter."""
        if not self.pages:
            start = self.full_text.find(chapter.title)
            if start < 0:
                return self.full_text if len(self.chapters) <= 1 else ""
            end = len(self.full_text)
            next_chapters = sorted(
                [c for c in self.chapters if c.order > chapter.order],
                key=lambda c: c.order,
            )
            for next_chapter in next_chapters:
                next_start = self.full_text.find(next_chapter.title, start + len(chapter.title))
                if next_start >= 0:
                    end = next_start
                    break
            return self.full_text[start:end].strip()

        if not chapter.page:
            return ""
        start_page = chapter.page
        end_page = self._find_next_chapter_page(chapter)
        chapter_pages = [
            p for p in self.pages if start_page <= p.number < end_page
        ]
        return "\n".join(p.text for p in chapter_pages)

    def _find_next_chapter_page(self, chapter: ChapterHeading) -> int:
        siblings = sorted(
            [c for c in self.chapters if c.level <= chapter.level and c.order > chapter.order],
            key=lambda c: c.order,
        )
        if siblings:
            return siblings[0].page or self.pages[-1].number + 1 if self.pages else 0
        return self.pages[-1].number + 1 if self.pages else 0


def document_from_dict(data: dict) -> Document:
    """Restore a Document from JSON-compatible storage data."""
    pages = [Page(**p) for p in data.get("pages", [])]
    chapters = [ChapterHeading(**c) for c in data.get("chapters", [])]
    return Document(
        filename=data.get("filename", ""),
        file_type=data.get("file_type", ""),
        pages=pages,
        chapters=chapters,
        full_text=data.get("full_text", ""),
        char_count=data.get("char_count", 0),
    )
