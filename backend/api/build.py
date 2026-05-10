"""Build orchestration endpoints + WebSocket for progress."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.api.materials import get_document, get_project_materials
from backend.core.jobs import BUILD_STAGES, create_job, get_job
from backend.models.material import Chunk, Section
from backend.models.project import BuildStatus
from backend.processing.chunking import chunk_sections
from backend.processing.graph_builder import build_single_graph
from backend.processing.rag_index import build_rag_index
from backend.processing.sectioning import recognize_sections

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/build", tags=["build"])

# Track active WebSocket connections per project
_active_ws: dict[str, list[WebSocket]] = {}


async def _broadcast(job_dict: dict, project_id: str) -> None:
    """Push job state to all connected WebSocket clients for a project."""
    dead: list[WebSocket] = []
    for ws in _active_ws.get(project_id, []):
        try:
            await ws.send_json(job_dict)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _active_ws.get(project_id, []):
            _active_ws[project_id].remove(ws)


@router.websocket("/ws")
async def build_websocket(websocket: WebSocket, project_id: str):
    await websocket.accept()
    _active_ws.setdefault(project_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        _active_ws[project_id][:] = [ws for ws in _active_ws[project_id] if ws != websocket]


@router.post("", status_code=202)
async def start_build(project_id: str, body: dict | None = None) -> dict:
    """Start the full build pipeline. Returns job ID for tracking."""
    params = body or {}
    job = create_job(project_id, BUILD_STAGES)
    # Run build in background
    asyncio.create_task(_run_build(project_id, job, params))
    return {"jobId": job.id, "status": job.status.value}


@router.get("/{job_id}")
async def get_build_status(project_id: str, job_id: str) -> dict:
    job = get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Build job not found")
    return job.to_dict()


async def _run_build(project_id: str, job, params: dict | None = None) -> None:
    """Execute full build pipeline with progress updates."""
    job.start()
    await _broadcast(job.to_dict(), project_id)

    materials = get_project_materials(project_id)
    all_sections: list[Section] = []
    all_chunks: list[Chunk] = []

    # Stage 1: Parsing (already done on upload, verify)
    job.stage_start("parsing")
    await _broadcast(job.to_dict(), project_id)
    job.stage_progress("parsing", 1.0, f"{len(materials)} files parsed")
    job.stage_done("parsing")
    await _broadcast(job.to_dict(), project_id)

    # Stage 2: Sectioning
    job.stage_start("sectioning")
    await _broadcast(job.to_dict(), project_id)
    for i, (mat_id, mat) in enumerate(materials.items()):
        doc = get_document(mat_id)
        if doc:
            import dataclasses
            if dataclasses.is_dataclass(doc):
                sections = recognize_sections(mat, doc)
            else:
                continue  # not a Document dataclass
            all_sections.extend(sections)
        job.stage_progress("sectioning", (i + 1) / max(len(materials), 1))
        await _broadcast(job.to_dict(), project_id)
    job.stage_done("sectioning")
    await _broadcast(job.to_dict(), project_id)

    # Stage 3: Chunking
    job.stage_start("chunking")
    await _broadcast(job.to_dict(), project_id)
    p = params or {}
    chunk_size = p.get("chunkSize", p.get("chunk_size", 500))
    chunk_overlap = p.get("chunkOverlap", p.get("chunk_overlap", 100))
    all_chunks = chunk_sections(all_sections, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    job.stage_progress("chunking", 1.0, f"{len(all_chunks)} chunks")
    job.stage_done("chunking")
    await _broadcast(job.to_dict(), project_id)

    if not all_chunks:
        job.fail("No content extracted from materials")
        await _broadcast(job.to_dict(), project_id)
        return

    # Stage 4 & 5: KG construction + RAG indexing in PARALLEL
    from backend.api.graph import get_or_create_store

    store = get_or_create_store(project_id)

    async def run_kg():
        kg_stage = "kg_construction"
        job.stage_start(kg_stage)
        await _broadcast(job.to_dict(), project_id)
        try:
            groups = _group_chunks_for_graph(all_sections, all_chunks)
            if not groups:
                raise ValueError("No section-scoped chunks available for graph construction")
            for textbook, sections_chunks in groups.items():
                await build_single_graph(store, textbook, sections_chunks)
            job.stage_done(kg_stage)
        except Exception as exc:
            job.stage_fail(kg_stage, str(exc))
        await _broadcast(job.to_dict(), project_id)

    async def run_rag():
        rag_stage = "rag_indexing"
        job.stage_start(rag_stage)
        await _broadcast(job.to_dict(), project_id)
        try:
            await build_rag_index(project_id, all_chunks)
            job.stage_done(rag_stage)
        except Exception as exc:
            job.stage_fail(rag_stage, str(exc))
        await _broadcast(job.to_dict(), project_id)

    await asyncio.gather(run_kg(), run_rag())

    # Stage 6: Cross-textbook integration
    job.stage_start("cross_textbook_integration")
    await _broadcast(job.to_dict(), project_id)
    # Deferred — triggered separately from decisions endpoint
    job.stage_done("cross_textbook_integration")
    await _broadcast(job.to_dict(), project_id)

    # Stage 7: Essence generation
    job.stage_start("essence_generation")
    await _broadcast(job.to_dict(), project_id)
    # Deferred — triggered when teacher requests report
    job.stage_done("essence_generation")
    await _broadcast(job.to_dict(), project_id)

    if any(stage.status == BuildStatus.FAILED for stage in job.stages.values()):
        job.status = BuildStatus.PARTIAL
    else:
        job.complete()
    await _broadcast(job.to_dict(), project_id)


def _group_chunks_for_graph(
    sections: list[Section],
    chunks: list[Chunk],
) -> dict[str, list[tuple[str, str, list[Chunk]]]]:
    """Group chunks by textbook and section ID for KG construction."""
    sections_by_id = {section.id: section for section in sections}
    grouped: dict[str, dict[str, list[Chunk]]] = {}
    for chunk in chunks:
        section = sections_by_id.get(chunk.section_id)
        if section is None:
            continue
        grouped.setdefault(section.textbook, {}).setdefault(section.id, []).append(chunk)

    return {
        textbook: [
            (section_id, sections_by_id[section_id].chapter, section_chunks)
            for section_id, section_chunks in section_map.items()
        ]
        for textbook, section_map in grouped.items()
    }
