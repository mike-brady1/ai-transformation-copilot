import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.digital_maturity import MATURITY_CATEGORIES
from backend.api.main import app
from backend.database import Base, get_db
from backend.rag.vector_store import get_chroma_client
from tests.conftest import fresh_chroma_client, reset_shared_chroma_store

# Deliberately uneven scores (2,2,2,2,2,2,3,3,3 like the real Colab run)
# and one category entirely missing, to prove the defensive fallback
# works, not just the happy path.
_SCORES = {"leadership": 2, "operations": 2, "technology": 2, "data": 2, "supply_chain": 2}


class _FakeToolUseBlock:
    def __init__(self, input_data):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def create(self, **kwargs):
        payload = {
            category: {"score": score, "justification": "..."}
            for category, score in _SCORES.items()
        }
        payload["automation"] = {"score": 2, "justification": "..."}
        payload["sustainability"] = {"score": 3, "justification": "Insufficient evidence."}
        # "cybersecurity" intentionally omitted entirely — simulates
        # Claude dropping a whole required category, not just a field.
        payload["workforce"] = {"score": 3, "justification": "..."}
        return _FakeResponse([_FakeToolUseBlock(payload)])


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


def test_maturity_requires_documents_first(client, workspace_id):
    resp = client.post(f"/workspaces/{workspace_id}/maturity")
    assert resp.status_code == 400


def test_maturity_computes_overall_and_survives_missing_category(client, workspace_id):
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

    resp = client.post(f"/workspaces/{workspace_id}/maturity")
    assert resp.status_code == 200
    body = resp.json()

    for category in MATURITY_CATEGORIES:
        assert category in body

    # cybersecurity was never in the fake response at all — should have
    # fallen back to the neutral score instead of a 500.
    assert body["cybersecurity"]["score"] == 3

    # 2,2,2,2,2,2,3,3,3 -> mean 2.333... -> rounded to 2.3, computed by
    # our own code, not asked of Claude.
    assert body["overall"] == 2.3


def test_maturity_rejects_unknown_workspace(client):
    resp = client.post("/workspaces/999/maturity")
    assert resp.status_code == 404
