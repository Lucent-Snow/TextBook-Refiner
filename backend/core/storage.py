"""Local filesystem storage helpers for project data."""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.core.config import settings

SAFE_STORAGE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class StoragePathError(ValueError):
    """Raised when a storage identifier would escape the project data root."""


def validate_storage_id(value: str, field_name: str = "id") -> str:
    if not value or not SAFE_STORAGE_ID_RE.fullmatch(value):
        raise StoragePathError(f"Invalid {field_name}")
    return value


def get_data_root() -> Path:
    return Path(settings.data_root)


def get_project_dir(project_id: str) -> Path:
    validate_storage_id(project_id, "project_id")
    projects_dir = get_projects_dir().resolve()
    project_dir = (projects_dir / project_id).resolve()
    if project_dir != projects_dir / project_id:
        raise StoragePathError("Invalid project_id")
    return project_dir


def get_projects_dir() -> Path:
    return (get_data_root() / "projects").resolve()


def ensure_project_dirs(project_id: str) -> dict[str, Path]:
    """Create all project subdirectories and return their paths."""
    base = get_project_dir(project_id)
    dirs = {
        "root": base,
        "materials": base / "materials",
        "parsed": base / "parsed",
        "chunks": base / "chunks",
        "graph": base / "graph",
        "chroma": base / "chroma",
        "reports": base / "reports",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def save_json(path: str | Path, data: dict | list) -> None:
    """Save data as JSON file, creating parent dirs if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def load_json(path: str | Path) -> dict | list:
    """Load a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_upload(project_id: str, material_id: str, filename: str, content: bytes) -> str:
    """Save an uploaded file under the project materials directory."""
    validate_storage_id(material_id, "material_id")
    safe_name = Path(filename).name or "unknown"
    upload_dir = ensure_project_dirs(project_id)["materials"]
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{material_id}_{safe_name}"
    dest.write_bytes(content)
    return str(dest)


def append_jsonl(path: str | Path, entry: dict) -> None:
    """Append a single JSON line to a JSONL file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def exists(path: str | Path) -> bool:
    return Path(path).exists()
