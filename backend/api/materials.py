"""Material upload and listing endpoints."""

from __future__ import annotations

from dataclasses import asdict
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.storage import ensure_project_dirs, load_json, save_json, save_upload
from backend.loaders import document_from_dict, load_excel, load_markdown, load_pdf, load_word
from backend.models.material import FileType, Material, ParseStatus

router = APIRouter(prefix="/api/projects/{project_id}/materials", tags=["materials"])

_materials: dict[str, dict[str, Material]] = {}  # project_id -> {material_id: Material}
_documents: dict[str, dict] = {}  # material_id -> parsed Document dataclass


@router.post("", status_code=201)
async def upload_material(project_id: str, file: UploadFile = File(...)) -> Material:
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    type_map = {
        ".pdf": FileType.PDF,
        ".md": FileType.MARKDOWN,
        ".docx": FileType.WORD,
        ".xlsx": FileType.EXCEL,
    }
    file_type = type_map.get(ext)
    if file_type is None:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    material = Material(
        id=f"mat_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        filename=filename,
        file_type=file_type,
        file_path="",
    )

    content = await file.read()
    material.file_path = save_upload(project_id, material.id, filename, content)

    _materials.setdefault(project_id, {})[material.id] = material

    # Try parsing immediately
    try:
        material.parse_status = ParseStatus.PARSING
        doc = _parse_by_type(material, content)
        _documents[material.id] = doc
        material.char_count = doc.char_count
        material.parse_status = ParseStatus.DONE
        _save_document(project_id, material.id, doc)
    except Exception:
        material.parse_status = ParseStatus.FAILED

    _save_material(project_id, material)

    return material


@router.get("")
async def list_materials(project_id: str) -> list[Material]:
    _load_materials_from_disk(project_id)
    return list(_materials.get(project_id, {}).values())


@router.get("/{material_id}")
async def get_material(project_id: str, material_id: str) -> Material:
    _load_materials_from_disk(project_id)
    mat = _materials.get(project_id, {}).get(material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    return mat


def _parse_by_type(material: Material, content: bytes):
    """Parse uploaded file by type, loading via temp file."""
    import tempfile
    ext = Path(material.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loader_map = {
            FileType.PDF: load_pdf,
            FileType.MARKDOWN: load_markdown,
            FileType.WORD: load_word,
            FileType.EXCEL: load_excel,
        }
        loader = loader_map.get(material.file_type)
        if not loader:
            raise ValueError(f"No loader for {material.file_type}")
        return loader(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def get_document(material_id: str) -> dict | None:
    if material_id not in _documents:
        for project_id in list(_materials.keys()):
            _load_document_from_disk(project_id, material_id)
    return _documents.get(material_id)


def get_project_materials(project_id: str) -> dict[str, Material]:
    _load_materials_from_disk(project_id)
    return _materials.get(project_id, {})


def _save_material(project_id: str, material: Material) -> None:
    dirs = ensure_project_dirs(project_id)
    save_json(dirs["materials"] / f"{material.id}.json", material.model_dump(mode="json"))


def _save_document(project_id: str, material_id: str, document) -> None:
    dirs = ensure_project_dirs(project_id)
    save_json(dirs["parsed"] / f"{material_id}.json", asdict(document))


def _load_materials_from_disk(project_id: str) -> None:
    dirs = ensure_project_dirs(project_id)
    project_materials = _materials.setdefault(project_id, {})
    for metadata_file in dirs["materials"].glob("mat_*.json"):
        try:
            data = load_json(metadata_file)
            material = Material(**data)
            project_materials.setdefault(material.id, material)
        except Exception:
            continue


def _load_document_from_disk(project_id: str, material_id: str) -> None:
    dirs = ensure_project_dirs(project_id)
    parsed_file = dirs["parsed"] / f"{material_id}.json"
    if not parsed_file.exists():
        return
    try:
        data = load_json(parsed_file)
        _documents[material_id] = document_from_dict(data)
    except Exception:
        return
