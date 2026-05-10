import sys
from types import ModuleType, SimpleNamespace

from backend.processing import rag_index


def test_local_chroma_client_is_cached_per_project(tmp_path, monkeypatch):
    created_paths: list[str] = []

    class FakeSettings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakePersistentClient:
        def __init__(self, path, settings):
            self.path = path
            self.settings = settings
            created_paths.append(path)

    chromadb_module = ModuleType("chromadb")
    chromadb_module.PersistentClient = FakePersistentClient
    chromadb_module.HttpClient = lambda **kwargs: SimpleNamespace(**kwargs)
    chromadb_config_module = ModuleType("chromadb.config")
    chromadb_config_module.Settings = FakeSettings

    monkeypatch.setitem(sys.modules, "chromadb", chromadb_module)
    monkeypatch.setitem(sys.modules, "chromadb.config", chromadb_config_module)
    monkeypatch.setattr("backend.core.config.settings.data_root", str(tmp_path))
    monkeypatch.setattr("backend.core.config.settings.chroma_host", None)
    rag_index._http_chroma_client = None
    rag_index._persistent_chroma_clients.clear()

    first = rag_index._get_chroma("proj_a")
    second = rag_index._get_chroma("proj_b")
    first_again = rag_index._get_chroma("proj_a")

    assert first is first_again
    assert first is not second
    assert len(created_paths) == 2
    assert "proj_a" in created_paths[0]
    assert "proj_b" in created_paths[1]
