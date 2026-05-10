"""Demo project seeding — pre-load medical textbooks on first startup."""

from __future__ import annotations

import logging
import shutil
from dataclasses import asdict
from pathlib import Path

from backend.core.storage import ensure_project_dirs, get_data_root, save_json
from backend.loaders.markdown import load_markdown
from backend.models.material import FileType, Material, ParseStatus
from backend.models.project import Project

logger = logging.getLogger(__name__)

DEMO_PROJECT_ID = "demo"

SEED_BOOKS = [
    {"id": "mat_01", "filename": "01_局部解剖学.md", "name": "局部解剖学"},
    {"id": "mat_02", "filename": "02_组织学与胚胎学.md", "name": "组织学与胚胎学"},
    {"id": "mat_03", "filename": "03_生理学.md", "name": "生理学"},
    {"id": "mat_04", "filename": "04_医学微生物学.md", "name": "医学微生物学"},
    {"id": "mat_05", "filename": "05_病理学.md", "name": "病理学"},
    # 06_传染病学 and 07_病理生理学 — data extraction in progress
]

SEED_DIR = Path(__file__).resolve().parent


def seed_demo_project() -> dict | None:
    """Create demo project with pre-loaded textbooks if it doesn't exist.

    Returns project dict if created, None if already exists.
    Idempotent — safe to call on every startup.
    """
    data_root = get_data_root()
    project_dir = data_root / "projects" / DEMO_PROJECT_ID

    if (project_dir / "project.json").exists():
        logger.info("Demo project already exists, skipping seed")
        return None

    project = Project(
        id=DEMO_PROJECT_ID,
        name="医学教材知识整合",
    )
    dirs = ensure_project_dirs(DEMO_PROJECT_ID)
    save_json(dirs["root"] / "project.json", project.model_dump(mode="json"))

    count = 0
    for book in SEED_BOOKS:
        src = SEED_DIR / book["filename"]
        if not src.exists():
            logger.warning("Seed file not found: %s", src)
            continue

        dest = dirs["materials"] / f"{book['id']}_{book['filename']}"
        shutil.copy2(src, dest)

        doc = load_markdown(dest)
        save_json(dirs["parsed"] / f"{book['id']}.json", asdict(doc))

        material = Material(
            id=book["id"],
            project_id=DEMO_PROJECT_ID,
            filename=book["name"],
            file_type=FileType.MARKDOWN,
            file_path=str(dest),
            parse_status=ParseStatus.DONE,
            char_count=doc.char_count,
        )
        save_json(
            dirs["materials"] / f"{book['id']}.json",
            material.model_dump(mode="json"),
        )
        count += 1
        logger.info(
            "Seeded %s: %d chars, %d chapters",
            book["name"], doc.char_count, len(doc.chapters),
        )

    logger.info("Demo project created with %d textbooks", count)
    return project.model_dump(mode="json")
