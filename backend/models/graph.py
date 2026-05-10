from datetime import datetime
from enum import Enum
from typing import Optional

from backend.models.base import CamelModel
from pydantic import Field


class NodeType(str, Enum):
    TEXTBOOK = "textbook"
    CHAPTER = "chapter"
    CONCEPT = "concept"


class RelationType(str, Enum):
    CONTAINS = "contains"
    PREREQUISITE = "prerequisite"
    PARALLEL = "parallel"
    CONTAINMENT = "containment"
    APPLICATION = "application"
    CAUSES = "causes"
    BELONGS_TO = "belongs_to"
    MANIFESTS_AS = "manifests_as"
    LOCATED_IN = "located_in"
    RELATED_TO = "related_to"
    DUPLICATE = "duplicate"
    COMPLEMENTARY = "complementary"
    MISSING = "missing"


class Evidence(CamelModel):
    material_id: str
    textbook: str
    chapter: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    quote: str


class KnowledgeNode(CamelModel):
    id: str
    type: NodeType
    label: str
    definition: str = ""
    sources: list[str] = Field(default_factory=list)
    frequency: int = 1
    merge_status: Optional[str] = None
    teacher_overrides: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeEdge(CamelModel):
    id: str
    source: str
    target: str
    relation: RelationType
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphOperation(CamelModel):
    id: str
    operation: str
    params: dict = Field(default_factory=dict)
    reason: str = ""
    success: bool = False
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
