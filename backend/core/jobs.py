"""In-memory build job state machine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.models.project import BuildStatus, StageProgress


class BuildJob:
    """Track a long-running build across multiple stages."""

    def __init__(self, project_id: str, stage_names: list[str]):
        self.id = f"job_{uuid.uuid4().hex[:12]}"
        self.project_id = project_id
        self.status = BuildStatus.PENDING
        self.stages: dict[str, StageProgress] = {
            name: StageProgress(name=name) for name in stage_names
        }
        self.current_stage: str | None = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def start(self) -> None:
        self.status = BuildStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def stage_start(self, name: str) -> None:
        self.current_stage = name
        stage = self.stages[name]
        stage.status = BuildStatus.RUNNING
        self.updated_at = datetime.now(timezone.utc)

    def stage_progress(self, name: str, progress: float, message: str = "") -> None:
        stage = self.stages[name]
        stage.progress = progress
        stage.message = message
        self.updated_at = datetime.now(timezone.utc)

    def stage_done(self, name: str) -> None:
        stage = self.stages[name]
        stage.status = BuildStatus.COMPLETED
        stage.progress = 1.0
        self.updated_at = datetime.now(timezone.utc)

    def stage_fail(self, name: str, error: str) -> None:
        stage = self.stages[name]
        stage.status = BuildStatus.FAILED
        stage.error = error
        self.status = BuildStatus.PARTIAL
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        self.status = BuildStatus.COMPLETED
        self.current_stage = None
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, error: str) -> None:
        self.status = BuildStatus.FAILED
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "status": self.status.value,
            "stages": {
                name: {
                    "name": s.name,
                    "status": s.status.value,
                    "progress": s.progress,
                    "message": s.message,
                    "error": s.error,
                }
                for name, s in self.stages.items()
            },
            "currentStage": self.current_stage,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }


# In-memory store
_jobs: dict[str, BuildJob] = {}


def create_job(project_id: str, stage_names: list[str]) -> BuildJob:
    job = BuildJob(project_id, stage_names)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> BuildJob | None:
    return _jobs.get(job_id)


# Standard build stages
BUILD_STAGES = [
    "parsing",
    "sectioning",
    "chunking",
    "kg_construction",
    "rag_indexing",
    "cross_textbook_integration",
    "essence_generation",
]
