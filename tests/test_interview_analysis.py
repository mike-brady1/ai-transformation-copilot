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
