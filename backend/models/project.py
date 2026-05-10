from datetime import datetime
from enum import Enum
from typing import Optional

from backend.models.base import CamelModel
from pydantic import Field


class BuildStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class Project(CamelModel):
    id: str
    name: str
    status: BuildStatus = BuildStatus.PENDING
    compression_target: float = 0.3
    original_char_count: int = 0
    essence_char_count: int = 0
    compression_ratio: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StageProgress(CamelModel):
    name: str
    status: BuildStatus = BuildStatus.PENDING
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None


class BuildJob(CamelModel):
    id: str
    project_id: str
    status: BuildStatus = BuildStatus.PENDING
    stages: dict[str, StageProgress] = Field(default_factory=dict)
    current_stage: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
