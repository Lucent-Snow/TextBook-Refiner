"""Integration decision management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.graph.tools import add_edge, merge_nodes, remove_edge, restore_node, split_node, update_definition
from backend.models.decision import DecisionStatus, DecisionType, IntegrationDecision
from backend.processing.integration import detect_cross_textbook, detect_missing_points

router = APIRouter(prefix="/api/projects/{project_id}/decisions", tags=["decisions"])

_decisions: dict[str, dict[str, IntegrationDecision]] = {}  # project_id -> {decision_id: decision}


def get_project_decisions(project_id: str) -> dict[str, IntegrationDecision]:
    return _decisions.get(project_id, {})


@router.get("")
async def list_decisions(project_id: str) -> list[IntegrationDecision]:
    return list(_decisions.get(project_id, {}).values())


@router.post("/detect", status_code=201)
async def run_integration_detection(project_id: str) -> list[IntegrationDecision]:
    """Run cross-textbook integration detection on the current graph."""
    from backend.api.graph import get_or_create_store
    store = get_or_create_store(project_id)

    decisions = await detect_cross_textbook(project_id, store)
    _decisions.setdefault(project_id, {})
    for d in decisions:
        _decisions[project_id][d.id] = d

    # Also detect missing knowledge points
    missing = await detect_missing_points(project_id, store)
    for mp in missing:
        dec = IntegrationDecision(
            id=f"dec_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            type=DecisionType.MISSING,
            involved_node_ids=mp.get("between_nodes", []),
            reason=mp.get("reason", ""),
            confidence=0.6,
        )
        _decisions[project_id][dec.id] = dec
        decisions.append(dec)

    return decisions


@router.post("/{decision_id}/accept")
async def accept_decision(project_id: str, decision_id: str, body: dict | None = None) -> dict:
    """Accept an integration decision and apply its suggested graph operation."""
    dec = _decisions.get(project_id, {}).get(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    from backend.api.graph import get_or_create_store
    store = get_or_create_store(project_id)

    op = dec.suggested_operation or {}
    op_name = op.get("operation", "")
    params = op.get("params", {})

    result = {"applied": False, "operation": op_name}

    if op_name == "merge_nodes":
        result.update(merge_nodes(
            store,
            node_ids=params.get("node_ids", dec.involved_node_ids),
            canonical_name=params.get("canonical_name", "merged"),
            reason=dec.reason,
        ))
        result["applied"] = bool(result.get("merged"))
    elif op_name == "add_edge":
        result.update(add_edge(
            store,
            source=params.get("source", ""),
            target=params.get("target", ""),
            relation=params.get("relation", "related_to"),
            confidence=dec.confidence,
        ))
        result["applied"] = bool(result.get("added"))
    elif op_name == "remove_edge":
        result.update(remove_edge(
            store,
            source=params.get("source", ""),
            target=params.get("target", ""),
            reason=dec.reason,
        ))
        result["applied"] = bool(result.get("removed"))
    elif op_name == "split_node":
        result.update(split_node(
            store,
            node_id=params.get("node_id", ""),
            new_nodes=params.get("new_nodes", []),
            reason=dec.reason,
        ))
        result["applied"] = bool(result.get("split"))
    elif op_name == "update_definition":
        result.update(update_definition(
            store,
            node_id=params.get("node_id", ""),
            definition=params.get("definition", ""),
            reason=dec.reason,
        ))
        result["applied"] = bool(result.get("updated"))
    elif op_name == "restore_node":
        result.update(restore_node(
            store,
            node_id=params.get("node_id", ""),
            reason=dec.reason,
        ))
        result["applied"] = bool(result.get("restored"))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {op_name}")

    if not result.get("applied"):
        raise HTTPException(status_code=400, detail=result.get("error", "Decision operation failed"))

    dec.status = DecisionStatus.ACCEPTED
    dec.teacher_feedback = (body or {}).get("note")

    return result


@router.post("/{decision_id}/reject")
async def reject_decision(project_id: str, decision_id: str, body: dict) -> dict:
    """Reject an integration decision."""
    dec = _decisions.get(project_id, {}).get(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    dec.status = DecisionStatus.REJECTED
    dec.teacher_feedback = body.get("reason", "")
    return {"rejected": True, "decisionId": decision_id}
