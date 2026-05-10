from datetime import datetime
from enum import Enum
from typing import Optional

from backend.models.base import CamelModel
from pydantic import Field


class DecisionType(str, Enum):
    DUPLICATE = "duplicate"
    COMPLEMENTARY = "complementary"
    MISSING = "missing"
    CONFLICT = "conflict"


class DecisionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISED = "revised"


class IntegrationDecision(CamelModel):
    id: str
    project_id: str
    type: DecisionType
    status: DecisionStatus = DecisionStatus.PENDING
    involved_node_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    suggested_operation: Optional[dict] = None
    teacher_feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
