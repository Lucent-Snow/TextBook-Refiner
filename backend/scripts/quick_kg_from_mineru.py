"""Build a live structural KG from MinerU Markdown outputs.

This is a deterministic bootstrap graph: textbook -> chapter -> heading concepts,
plus sequential prerequisite edges. LLM enrichment can run after the graph is visible.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from backend.core.config import settings

DATA_ROOT = Path(settings.data_root)
PROJECT_ID = "proj_live_kg"
PROJECT_NAME = "Live Textbook KG"
MINERU_ROOT = Path(r"E:\Desktop\大学\比赛\浙大AI全栈极速黑客松！\mineru-output\backend")


def main() -> None:
    project_dir = DATA_ROOT / "projects" / PROJECT_ID
    graph_dir = project_dir / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    project = {
        "id": PROJECT_ID,
        "name": PROJECT_NAME,
        "status": "draft",
        "compressionRatio": 0,
        "createdAt": datetime.utcnow().isoformat(),
    }
    (project_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    for book_dir in sorted(MINERU_ROOT.iterdir()):
        if not book_dir.is_dir():
            continue
        md_path = _pick_markdown(book_dir)
        if md_path is None:
            continue

        textbook = book_dir.name
        textbook_id = _id("tb", textbook)
        _add_node(nodes, seen_nodes, textbook_id, "textbook", textbook)

        headings = _extract_headings(md_path.read_text(encoding="utf-8"))
        current_chapter_id: str | None = None
        chapter_concepts = 0
        previous_concept_id: str | None = None
        chapters_seen = 0

        for heading in headings:
            if heading["level"] == 1:
                chapters_seen += 1
                if chapters_seen > 24:
                    continue
                current_chapter_id = _id("ch", f"{textbook}:{heading['title']}")
                previous_concept_id = None
                chapter_concepts = 0
                _add_node(nodes, seen_nodes, current_chapter_id, "chapter", heading["title"])
                _add_edge(edges, seen_edges, textbook_id, current_chapter_id, "contains")
                continue

            if current_chapter_id is None or chapter_concepts >= 10:
                continue

            concept_id = _id("cn", f"{textbook}:{current_chapter_id}:{heading['title']}")
            _add_node(
                nodes,
                seen_nodes,
                concept_id,
                "concept",
                heading["title"],
                definition=f"来自《{textbook}》的教材结构标题，等待 LLM 补充定义与关系。",
                sources=[str(md_path.name)],
            )
            _add_edge(edges, seen_edges, current_chapter_id, concept_id, "contains")
            if previous_concept_id:
                _add_edge(edges, seen_edges, previous_concept_id, concept_id, "prerequisite", confidence=0.45)
            previous_concept_id = concept_id
            chapter_concepts += 1

    (graph_dir / "graph.json").write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"project_id={PROJECT_ID}")
    print(f"nodes={len(nodes)} edges={len(edges)}")


def _pick_markdown(book_dir: Path) -> Path | None:
    merged = book_dir / f"{book_dir.name}.mineru.md"
    if merged.exists():
        return merged
    md_files = sorted(book_dir.glob("*.md"))
    return md_files[0] if md_files else None


def _extract_headings(text: str) -> list[dict]:
    headings: list[dict] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line.strip())
        if not match:
            continue
        title = _normalize(match.group(1))
        if not _is_heading(title):
            continue
        level = _level(title)
        if headings and headings[-1]["title"] == title and headings[-1]["level"] == level:
            continue
        headings.append({"title": title, "level": level})
    return headings


def _normalize(title: str) -> str:
    title = re.sub(r"\s+", " ", title.replace("\u3000", " ")).strip()
    title = title.replace(" | ", " ")
    title = re.sub(r"\s*[.。·]+\s*\d+\s*$", "", title).strip()
    return title[:80]


def _is_heading(title: str) -> bool:
    if not title or len(title) > 80:
        return False
    if title in {"Pathology", "病理学", "版权所有，侵权必究！"}:
        return False
    if re.match(r"^第[一二三四五六七八九十百千\d]+[章节].*\s+\d+$", title):
        return False
    return bool(
        re.match(r"^(绪\s*论|第[一二三四五六七八九十百千\d]+章\b)", title)
        or re.match(r"^第[一二三四五六七八九十百千\d]+节\b", title)
        or re.match(r"^[一二三四五六七八九十]+、", title)
        or re.match(r"^（[一二三四五六七八九十]+）", title)
    )


def _level(title: str) -> int:
    if re.match(r"^(绪\s*论|第[一二三四五六七八九十百千\d]+章\b)", title):
        return 1
    if re.match(r"^第[一二三四五六七八九十百千\d]+节\b", title):
        return 2
    return 3


def _id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]}"


def _add_node(
    nodes: list[dict],
    seen: set[str],
    node_id: str,
    node_type: str,
    label: str,
    definition: str = "",
    sources: list[str] | None = None,
) -> None:
    if node_id in seen:
        return
    seen.add(node_id)
    nodes.append({
        "id": node_id,
        "type": node_type,
        "label": label,
        "definition": definition,
        "sources": sources or [],
        "frequency": 1,
        "merge_status": None,
        "teacher_overrides": {},
    })


def _add_edge(
    edges: list[dict],
    seen: set[tuple[str, str, str]],
    source: str,
    target: str,
    relation: str,
    confidence: float = 0.7,
) -> None:
    key = (source, target, relation)
    if key in seen:
        return
    seen.add(key)
    edges.append({
        "id": _id("e", f"{source}:{target}:{relation}"),
        "source": source,
        "target": target,
        "relation": relation,
        "evidence": [],
        "confidence": confidence,
    })


if __name__ == "__main__":
    main()
