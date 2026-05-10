"""Report generation and retrieval endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.agents.report_agent import run_report_agent
from backend.core.storage import ensure_project_dirs, load_json, save_json
from backend.models.report import IntegrationReport, TeachingFlowStep
from backend.processing.flow import generate_teaching_flow

router = APIRouter(prefix="/api/projects/{project_id}/report", tags=["report"])


@router.post("/generate", status_code=201)
async def generate_report(project_id: str) -> dict:
    """Generate the integration report with teaching flow, essence, and compression ratio."""
    from backend.api.graph import get_or_create_store
    from backend.api.decisions import get_project_decisions
    from backend.api.materials import get_project_materials, get_document

    store = get_or_create_store(project_id)
    snapshot = {"nodes": store.get_all_nodes(), "edges": store.get_all_edges()}

    decisions_map = get_project_decisions(project_id)
    decisions = [d.model_dump(mode="json") for d in decisions_map.values()]
    accepted = sum(1 for d in decisions_map.values() if d.status.value == "accepted")
    rejected = sum(1 for d in decisions_map.values() if d.status.value == "rejected")

    # Concatenate all original text
    materials = get_project_materials(project_id)
    all_text = ""
    for mat_id in materials:
        doc = get_document(mat_id)
        if doc:
            import dataclasses
            if dataclasses.is_dataclass(doc):
                all_text += doc.full_text

    if not all_text:
        # Fallback: collect from concepts
        all_text = " ".join(
            n.get("definition", "") for n in snapshot["nodes"] if n.get("type") == "concept"
        )

    # Generate teaching flow via topological sort (FLOW rule)
    flow_result = generate_teaching_flow(store)

    result = await run_report_agent(
        project_id=project_id,
        store_snapshot=snapshot,
        all_text=all_text,
        decisions=decisions,
        accepted_count=accepted,
        rejected_count=rejected,
        flow_result=flow_result,
    )

    # Use topological sort steps as primary teaching flow
    teaching_flow = [
        TeachingFlowStep(
            order=step["order"],
            concept_id=step["concept_id"],
            concept_label=step["concept_label"],
            textbook_refs=step.get("textbook_refs", []),
            prerequisite_ids=step["prerequisite_ids"],
        )
        for step in flow_result["steps"]
    ]

    # Merge decision summary
    decisions_summary = result.get("decisions_summary", {
        "accepted": accepted,
        "rejected": rejected,
        "total": len(decisions),
    })
    decisions_summary["conflicts"] = flow_result.get("conflicts", [])

    # Persist report
    report = IntegrationReport(
        id=f"rpt_{uuid.uuid4().hex[:12]}",
        project_id=project_id,
        teaching_flow=teaching_flow,
        decisions_summary=decisions_summary,
        essence_content=result.get("essence", ""),
        original_char_count=result.get("original_char_count", 0),
        essence_char_count=result.get("essence_char_count", 0),
        compression_ratio=result.get("compression_ratio", 0.0),
    )

    dirs = ensure_project_dirs(project_id)
    save_json(dirs["reports"] / f"{report.id}.json", report.model_dump(mode="json"))

    return report.model_dump(mode="json", by_alias=True)


@router.get("")
async def get_report(project_id: str) -> IntegrationReport:
    """Get the latest generated report."""
    dirs = ensure_project_dirs(project_id)
    reports_dir = dirs["reports"]
    report_files = sorted(reports_dir.glob("rpt_*.json"), reverse=True)
    if not report_files:
        raise HTTPException(status_code=404, detail="No report generated yet")
    data = load_json(report_files[0])
    return IntegrationReport(**data)
