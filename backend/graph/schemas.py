"""Graph data schemas for serialization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str  # textbook, chapter, concept
    label: str
    definition: str = ""
    sources: list[str] = field(default_factory=list)
    frequency: int = 1
    merge_status: str | None = None
    teacher_overrides: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str
    evidence: list[dict] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class GraphData:
    """Serializable graph snapshot."""
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
