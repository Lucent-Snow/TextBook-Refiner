from datetime import datetime

from backend.models.base import CamelModel
from pydantic import Field


class TeachingFlowStep(CamelModel):
    order: int
    concept_id: str
    concept_label: str
    textbook_refs: list[str] = Field(default_factory=list)
    prerequisite_ids: list[str] = Field(default_factory=list)


class IntegrationReport(CamelModel):
    id: str
    project_id: str
    teaching_flow: list[TeachingFlowStep] = Field(default_factory=list)
    decisions_summary: dict = Field(default_factory=dict)
    essence_content: str = ""
    original_char_count: int = 0
    essence_char_count: int = 0
    compression_ratio: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
