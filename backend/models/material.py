from datetime import datetime
from enum import Enum
from typing import Optional

from backend.models.base import CamelModel
from pydantic import Field


class FileType(str, Enum):
    PDF = "pdf"
    MARKDOWN = "md"
    WORD = "docx"
    EXCEL = "xlsx"


class ParseStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    DONE = "done"
    FAILED = "failed"


class Material(CamelModel):
    id: str
    project_id: str
    filename: str
    file_type: FileType
    file_path: str
    parse_status: ParseStatus = ParseStatus.PENDING
    char_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Section(CamelModel):
    id: str
    material_id: str
    textbook: str
    chapter: str
    order: int
    level: int = 1
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    char_count: int = 0
    text: str = ""


class Chunk(CamelModel):
    id: str
    section_id: str
    textbook: str
    chapter: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    text: str
    char_count: int = 0
    chunk_index: int = 0

    def citation_metadata(self) -> dict:
        return {
            "chunk_id": self.id,
            "textbook": self.textbook,
            "chapter": self.chapter,
            "page_start": self.page_start,
            "page_end": self.page_end,
        }
