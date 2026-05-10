"""Project CRUD endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.core.storage import ensure_project_dirs, get_projects_dir, load_json, save_json
from backend.models.project import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])

# In-memory store (replace with DB later)
_projects: dict[str, Project] = {}


@router.post("", status_code=201)
async def create_project(body: dict) -> Project:
    _load_projects_from_disk()
    project = Project(
        id=f"proj_{uuid.uuid4().hex[:12]}",
        name=body.get("name", "Untitled"),
    )
    _projects[project.id] = project
    ensure_project_dirs(project.id)
    save_json(
        ensure_project_dirs(project.id)["root"] / "project.json",
        project.model_dump(mode="json"),
    )
    return project


@router.get("")
async def list_projects() -> list[Project]:
    _load_projects_from_disk()
    return list(_projects.values())


@router.get("/{project_id}")
async def get_project(project_id: str) -> Project:
    _load_projects_from_disk()
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _load_projects_from_disk() -> None:
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return
    for project_file in projects_dir.glob("*/project.json"):
        try:
            data = load_json(project_file)
            project = Project(**data)
            _projects.setdefault(project.id, project)
        except Exception:
            continue
