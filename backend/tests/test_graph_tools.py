from backend.graph.schemas import GraphNode
from backend.graph.store import GraphStore
from backend.graph.tools import merge_nodes


def test_merge_nodes_preserves_sources_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.config.settings.data_root", str(tmp_path))
    store = GraphStore("proj_graph")
    store.add_node(GraphNode(id="n1", type="concept", label="炎症", sources=["a"]))
    store.add_node(GraphNode(id="n2", type="concept", label="炎症反应", sources=["b"]))

    result = merge_nodes(store, ["n1", "n2"], "炎症", "duplicate")

    assert result["merged"] is True
    assert store.get_node("n1")["sources"] == ["a", "b"]
    assert store.get_node("n2")["merge_status"] == "merged_into_n1"
    assert store.get_operation_log()[0]["operation"] == "merge_nodes"
