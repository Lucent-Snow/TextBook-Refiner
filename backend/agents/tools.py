"""OpenAI function-call tool definitions for agents.

Agents output structured tool calls. Deterministic backend functions
(in graph/tools.py and processing/) perform the actual mutations.
"""

from __future__ import annotations

# Graph operation tools
GRAPH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "merge_nodes",
            "description": "Merge duplicate knowledge nodes and preserve provenance. All sources are combined into the canonical node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_ids": {"type": "array", "items": {"type": "string"}, "description": "IDs of nodes to merge. First becomes canonical."},
                    "canonical_name": {"type": "string", "description": "Name for the merged node."},
                    "reason": {"type": "string", "description": "Why these nodes should be merged, with evidence."},
                },
                "required": ["node_ids", "canonical_name", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "split_node",
            "description": "Split a knowledge node into multiple distinct concepts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "ID of the node to split."},
                    "new_nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "definition": {"type": "string"},
                                "type": {"type": "string", "default": "concept"},
                            },
                            "required": ["label", "definition"],
                        },
                    },
                    "reason": {"type": "string"},
                },
                "required": ["node_id", "new_nodes", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_edge",
            "description": "Add a typed relationship edge between two knowledge nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source node ID."},
                    "target": {"type": "string", "description": "Target node ID."},
                    "relation": {"type": "string", "enum": ["prerequisite", "parallel", "containment", "application", "complementary"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence_quote": {"type": "string", "description": "Supporting quote from the textbook."},
                },
                "required": ["source", "target", "relation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_edge",
            "description": "Remove an incorrect or redundant edge between nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["source", "target", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_definition",
            "description": "Update a knowledge node's definition based on teacher feedback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "definition": {"type": "string", "description": "New corrected definition."},
                    "reason": {"type": "string", "description": "Why the definition is being changed."},
                },
                "required": ["node_id", "definition", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restore_node",
            "description": "Restore a node that was previously merged into another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["node_id", "reason"],
            },
        },
    },
]

# Integration decision tools
INTEGRATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "accept_decision",
            "description": "Accept an integration decision and apply the suggested graph operation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "note": {"type": "string", "description": "Optional teacher note."},
                },
                "required": ["decision_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_decision",
            "description": "Reject an integration decision with a reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "reason": {"type": "string", "description": "Why this decision is rejected."},
                },
                "required": ["decision_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revise_decision",
            "description": "Propose a revised integration decision with different parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_id": {"type": "string"},
                    "revised_operation": {"type": "object", "description": "Modified graph operation."},
                    "reason": {"type": "string"},
                },
                "required": ["decision_id", "revised_operation", "reason"],
            },
        },
    },
]

# RAG / Evidence tools
EVIDENCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_chunks",
            "description": "Search textbook chunks by semantic similarity for evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node_evidence",
            "description": "Get all source chunks and evidence for a knowledge node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_with_citations",
            "description": "Answer a teacher question with textbook citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "The cited answer."},
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "textbook": {"type": "string"},
                                "chapter": {"type": "string"},
                                "page_range": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                        },
                    },
                },
                "required": ["answer", "citations"],
            },
        },
    },
]

# Report tools
REPORT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_teaching_flow",
            "description": "Generate an ordered teaching flow respecting prerequisite constraints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_notes": {"type": "boolean", "default": True},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_compression_ratio",
            "description": "Calculate the current compression ratio from original vs essence character counts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": "Export the integration report with all decisions, flow, and essence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["json", "markdown"], "default": "json"},
                },
            },
        },
    },
]


def build_tool_definitions(
    groups: list[str] | None = None,
) -> list[dict]:
    """Get tool definitions for specified groups. If None, returns all tools.

    Groups: graph, integration, evidence, report
    """
    all_tools = {
        "graph": GRAPH_TOOLS,
        "integration": INTEGRATION_TOOLS,
        "evidence": EVIDENCE_TOOLS,
        "report": REPORT_TOOLS,
    }
    if groups is None:
        groups = list(all_tools.keys())

    tools: list[dict] = []
    for g in groups:
        tools.extend(all_tools.get(g, []))
    return tools
