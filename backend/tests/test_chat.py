from fastapi.testclient import TestClient

from backend.main import app


async def _fake_dialogue_agent(**kwargs):
    return {"content": "已收到。", "tool_calls": [], "model_used": "test-model"}


def test_chat_endpoint_uses_default_timestamp(monkeypatch):
    monkeypatch.setattr("backend.api.chat.run_dialogue_agent", _fake_dialogue_agent)
    client = TestClient(app)

    response = client.post(
        "/api/projects/proj_test/chat",
        json={"message": "请解释这个节点", "contextNodeIds": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"]["createdAt"]
    assert body["message"]["content"] == "已收到。"
    assert body["toolCalls"] == []
    assert body["modelUsed"] == "test-model"
