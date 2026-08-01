import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.api.main import app
from backend.database import Base, get_db
from backend.models.document import Document
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
        # Never calls the real Anthropic API: no cost, no network, no
        # non-determinism in the test suite. Shaped exactly like what
        # analyze_transcript() expects back from a real tool_use response.
        return _FakeResponse(
            [
                _FakeToolUseBlock(
                    {
                        "findings": [
                            {
                                "pain_point": "High machine downtime",
                                "severity": "High",
                                "business_impact": "Lost production time weekly",
                                "recommendation": "Predictive Maintenance",
                            }
                        ]
                    }
                )
            ]
        )


class _FakeAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()


@pytest.fixture()
def test_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def client(test_engine):
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


def test_analyze_document_returns_structured_findings(client, workspace_id):
    file_content = b"Machine failures happen almost every week on line 3."
    upload_resp = client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = client.post(f"/workspaces/{workspace_id}/documents/{document_id}/analyze")
    assert resp.status_code == 200
    findings = resp.json()
    assert len(findings) == 1
    assert findings[0]["pain_point"] == "High machine downtime"
    assert findings[0]["severity"] == "High"


def test_analyze_rejects_document_from_other_workspace(client, workspace_id):
    file_content = b"Some notes."
    upload_resp = client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = client.post(f"/workspaces/999/documents/{document_id}/analyze")
    assert resp.status_code == 404


def test_analyze_fails_cleanly_when_chunks_are_missing(client, workspace_id, test_engine):
    """Regression test for a real production bug: a Document row can
    outlive its Chroma chunks (e.g. a host with an ephemeral disk that
    resets on redeploy while the database persists). Reproduced by
    inserting the DB row directly, bypassing the upload endpoint, so no
    chunks ever exist for it — exactly the state that crashed with an
    unhandled 500 in production."""
    with Session(test_engine) as db:
        ghost_document = Document(workspace_id=workspace_id, filename="ghost.txt", chunk_count=0)
        db.add(ghost_document)
        db.commit()
        db.refresh(ghost_document)
        document_id = ghost_document.id

    resp = client.post(f"/workspaces/{workspace_id}/documents/{document_id}/analyze")
    assert resp.status_code == 404
    assert "re-uploaded" in resp.json()["detail"]
