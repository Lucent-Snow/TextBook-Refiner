import pytest
from fastapi.testclient import TestClient

from backend.core.storage import StoragePathError, get_project_dir
from backend.main import app


def test_project_id_path_traversal_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.config.settings.data_root", str(tmp_path))

    with pytest.raises(StoragePathError):
        get_project_dir("..")


def test_invalid_project_id_returns_400(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.config.settings.data_root", str(tmp_path))
    client = TestClient(app)

    response = client.get("/api/projects/%2e%2e/materials")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_storage_id"
