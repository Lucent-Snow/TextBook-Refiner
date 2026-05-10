import pytest

from backend.api.build import _active_ws, _broadcast, _group_chunks_for_graph, _run_build
from backend.core.jobs import BUILD_STAGES, create_job
from backend.models.material import Chunk, Section


@pytest.mark.asyncio
async def test_build_without_materials_fails_instead_of_completing(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.config.settings.data_root", str(tmp_path))
    project_id = "proj_empty"
    job = create_job(project_id, BUILD_STAGES)

    await _run_build(project_id, job, {})

    assert job.status.value == "failed"


def test_group_chunks_for_graph_keeps_same_named_chapters_separate():
    sections = [
        Section(id="sec_a", material_id="mat_a", textbook="book_a", chapter="第一章 绪论", order=1),
        Section(id="sec_b", material_id="mat_b", textbook="book_b", chapter="第一章 绪论", order=1),
    ]
    chunks = [
        Chunk(id="chk_a", section_id="sec_a", textbook="book_a", chapter="第一章 绪论", text="A"),
        Chunk(id="chk_b", section_id="sec_b", textbook="book_b", chapter="第一章 绪论", text="B"),
    ]

    grouped = _group_chunks_for_graph(sections, chunks)

    assert grouped["book_a"] == [("sec_a", "第一章 绪论", [chunks[0]])]
    assert grouped["book_b"] == [("sec_b", "第一章 绪论", [chunks[1]])]


@pytest.mark.asyncio
async def test_build_broadcast_cleanup_tolerates_concurrent_disconnect():
    project_id = "proj_ws"

    class DisconnectingWebSocket:
        async def send_json(self, payload):
            _active_ws[project_id].remove(self)
            raise RuntimeError("disconnected")

    ws = DisconnectingWebSocket()
    _active_ws[project_id] = [ws]

    await _broadcast({"status": "running"}, project_id)

    assert _active_ws[project_id] == []
