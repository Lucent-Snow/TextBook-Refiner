"""Graph data endpoints + WebSocket for live updates."""

from __future__ import annotations

import logging
import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.graph.store import GraphStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/graph", tags=["graph"])

# Active graph WebSocket connections
_graph_ws: dict[str, list[WebSocket]] = {}
# Cached graph stores
_stores: dict[str, GraphStore] = {}


def get_or_create_store(project_id: str) -> GraphStore:
    if project_id not in _stores:
        _stores[project_id] = GraphStore(project_id)
        _stores[project_id].on_change(lambda snapshot: _schedule_broadcast(project_id, snapshot))
    return _stores[project_id]


def _schedule_broadcast(project_id: str, snapshot: dict) -> None:
    try:
        asyncio.get_running_loop().create_task(_broadcast_graph(project_id, snapshot))
    except RuntimeError:
        logger.debug("Skipped graph WebSocket broadcast outside an event loop")


async def _broadcast_graph(project_id: str, snapshot: dict) -> None:
    dead = []
    for ws in _graph_ws.get(project_id, []):
        try:
            await ws.send_json(snapshot)
        except Exception:
            dead.append(ws)
    # Cleanup dead connections
    for ws in dead:
        if ws in _graph_ws.get(project_id, []):
            _graph_ws[project_id].remove(ws)


@router.websocket("/ws")
async def graph_websocket(websocket: WebSocket, project_id: str):
    await websocket.accept()
    _graph_ws.setdefault(project_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _graph_ws[project_id][:] = [ws for ws in _graph_ws[project_id] if ws != websocket]


@router.get("")
async def get_graph(project_id: str) -> dict:
    store = get_or_create_store(project_id)
    return {"nodes": store.get_all_nodes(), "edges": store.get_all_edges()}


@router.get("/node/{node_id}")
async def get_node(project_id: str, node_id: str) -> dict:
    store = get_or_create_store(project_id)
    node = store.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node
