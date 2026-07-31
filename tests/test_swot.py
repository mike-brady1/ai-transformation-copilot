import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.api.main import app
from backend.database import Base, get_db
from backend.rag.vector_store import get_chroma_client
from tests.conftest import fresh_chroma_client, reset_shared_chroma_store


class _FakeToolUseBlock:
    def __init__(self, input_data):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def create(self, **kwargs):
        return _FakeResponse(
            [
                _FakeToolUseBlock(
                    {
                        "strengths": [{"item": "Experienced workforce", "explanation": "..."}],
                        "weaknesses": [{"item": "High machine downtime", "explanation": "..."}],
                        "opportunities": [{"item": "Predictive maintenance", "explanation": "..."}],
                        "threats": [{"item": "Production downtime costs", "explanation": "..."}],
                    }
                )
            ]
        )


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

    reset_shared_chroma_store()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma_client] = fresh_chroma_client
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


def test_swot_requires_documents_first(client, workspace_id):
    resp = client.post(f"/workspaces/{workspace_id}/swot")
    assert resp.status_code == 400


def test_swot_generates_all_four_quadrants(client, workspace_id):
    client.post(
        f"/workspaces/{workspace_id}/documents",
        files={
            "file": (
                "notes.txt",
                io.BytesIO(b"Machine failures happen almost every week."),
                "text/plain",
            )
        },
    )

    resp = client.post(f"/workspaces/{workspace_id}/swot")
    assert resp.status_code == 200
    swot = resp.json()
    assert swot["strengths"][0]["item"] == "Experienced workforce"
    assert swot["weaknesses"][0]["item"] == "High machine downtime"
    assert swot["opportunities"][0]["item"] == "Predictive maintenance"
    assert swot["threats"][0]["item"] == "Production downtime costs"


def test_swot_rejects_unknown_workspace(client):
    resp = client.post("/workspaces/999/swot")
    assert resp.status_code == 404
