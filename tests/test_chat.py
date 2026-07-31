import io

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.api.main import app
from backend.database import Base, get_db
from backend.rag.vector_store import get_chroma_client


class _FakeTextBlock:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def create(self, **kwargs):
        return _FakeResponse("This is a fake grounded answer.")


class _FakeAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()


@pytest.fixture()
def client(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = Session(test_engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma_client] = lambda: chromadb.EphemeralClient()
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropicClient()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def workspace_id(client):
    resp = client.post(
        "/workspaces",
        json={
            "client_name": "Acme Manufacturing",
            "industry": "Automotive",
            "employees": 1500,
            "countries": ["France"],
        },
    )
    return resp.json()["id"]


def test_chat_answers_with_sources(client, workspace_id):
    file_content = b"Machine failures happen almost every week on line 3."
    client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )

    resp = client.post(
        f"/workspaces/{workspace_id}/chat",
        json={"messages": [{"role": "user", "content": "What's causing downtime?"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "This is a fake grounded answer."
    assert "notes.txt" in body["sources"]


def test_chat_rejects_unknown_workspace(client):
    resp = client.post(
        "/workspaces/999/chat",
        json={"messages": [{"role": "user", "content": "Anything?"}]},
    )
    assert resp.status_code == 404
